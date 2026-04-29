#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

static void require_size(int size, int expected, int rank) {
    if (size != expected) {
        if (rank == 0) {
            fprintf(stderr, "test_nonblocking_any_source_wait requires %d ranks, got %d\n", expected, size);
        }
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
}

int main(int argc, char **argv) {
    int rank, size;
    int msg1 = 111;
    int msg2 = 222;
    int go = 1;
    int recvbuf[4] = {-1, -1, -1, -1};
    int tail = -1;
    int count = -1;
    MPI_Request req;
    MPI_Status status;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    require_size(size, 3, rank);

    if (rank == 0) {
        MPI_Irecv(recvbuf, 4, MPI_INT, MPI_ANY_SOURCE, 50, MPI_COMM_WORLD, &req);
        MPI_Wait(&req, &status);
        MPI_Get_count(&status, MPI_INT, &count);

        if (status.MPI_SOURCE != 1 || count != 1 || recvbuf[0] != 111) {
            fprintf(stderr,
                    "rank 0 expected ANY_SOURCE Irecv/Wait from rank 1, count 1, value 111; got source=%d count=%d value=%d\n",
                    status.MPI_SOURCE, count, recvbuf[0]);
            MPI_Abort(MPI_COMM_WORLD, 2);
        }

        MPI_Send(&go, 1, MPI_INT, 2, 51, MPI_COMM_WORLD);

        MPI_Recv(&tail, 1, MPI_INT, 2, 50, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        if (tail != 222) {
            fprintf(stderr, "rank 0 expected second value 222, got %d\n", tail);
            MPI_Abort(MPI_COMM_WORLD, 3);
        }
    } else if (rank == 1) {
        MPI_Send(&msg1, 1, MPI_INT, 0, 50, MPI_COMM_WORLD);
    } else if (rank == 2) {
        MPI_Recv(&go, 1, MPI_INT, 0, 51, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        MPI_Send(&msg2, 1, MPI_INT, 0, 50, MPI_COMM_WORLD);
    }

    MPI_Finalize();
    return 0;
}

