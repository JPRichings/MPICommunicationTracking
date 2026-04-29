#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

static void require_size(int size, int expected, int rank) {
    if (size != expected) {
        if (rank == 0) {
            fprintf(stderr, "test_test requires %d ranks, got %d\n", expected, size);
        }
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
}

int main(int argc, char **argv) {
    int rank, size;
    int ready = 1;
    int flag = 0;
    int sendv = 900;
    int recvv[4] = {-1, -1, -1, -1};
    int count = -1;
    MPI_Request req;
    MPI_Status status;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    require_size(size, 2, rank);

    if (rank == 0) {
        MPI_Recv(&ready, 1, MPI_INT, 1, 91, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        MPI_Send(&sendv, 1, MPI_INT, 1, 90, MPI_COMM_WORLD);
    } else {
        MPI_Irecv(recvv, 4, MPI_INT, 0, 90, MPI_COMM_WORLD, &req);
        MPI_Send(&ready, 1, MPI_INT, 0, 91, MPI_COMM_WORLD);

        while (!flag) {
            MPI_Test(&req, &flag, &status);
        }

        MPI_Get_count(&status, MPI_INT, &count);
        if (status.MPI_SOURCE != 0 || count != 1 || recvv[0] != 900) {
            fprintf(stderr,
                    "rank 1 expected Test completion from rank 0, count 1, value 900; got source=%d count=%d value=%d\n",
                    status.MPI_SOURCE, count, recvv[0]);
            MPI_Abort(MPI_COMM_WORLD, 2);
        }
    }

    MPI_Finalize();
    return 0;
}

