#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

static void require_size(int size, int expected, int rank) {
    if (size != expected) {
        if (rank == 0) {
            fprintf(stderr, "test_waitany requires %d ranks, got %d\n", expected, size);
        }
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
}

int main(int argc, char **argv) {
    int rank, size;
    int ready = 1;
    int ack = 1;
    int send0 = 100;
    int send1 = 101;
    int recv0[4] = {-1, -1, -1, -1};
    int recv1[4] = {-1, -1, -1, -1};
    int index = -1;
    int count = -1;
    MPI_Request reqs[2];
    MPI_Status status;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    require_size(size, 2, rank);

    if (rank == 0) {
        MPI_Recv(&ready, 1, MPI_INT, 1, 62, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        MPI_Send(&send0, 1, MPI_INT, 1, 60, MPI_COMM_WORLD);
        MPI_Recv(&ack, 1, MPI_INT, 1, 63, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        MPI_Send(&send1, 1, MPI_INT, 1, 61, MPI_COMM_WORLD);
    } else {
        MPI_Irecv(recv0, 4, MPI_INT, 0, 60, MPI_COMM_WORLD, &reqs[0]);
        MPI_Irecv(recv1, 4, MPI_INT, 0, 61, MPI_COMM_WORLD, &reqs[1]);

        MPI_Send(&ready, 1, MPI_INT, 0, 62, MPI_COMM_WORLD);

        MPI_Waitany(2, reqs, &index, &status);
        MPI_Get_count(&status, MPI_INT, &count);

        if (index != 0 || status.MPI_SOURCE != 0 || count != 1 || recv0[0] != 100) {
            fprintf(stderr,
                    "rank 1 expected Waitany to complete index 0 from rank 0, count 1, value 100; got index=%d source=%d count=%d value=%d\n",
                    index, status.MPI_SOURCE, count, recv0[0]);
            MPI_Abort(MPI_COMM_WORLD, 2);
        }

        MPI_Send(&ack, 1, MPI_INT, 0, 63, MPI_COMM_WORLD);

        MPI_Wait(&reqs[1], MPI_STATUS_IGNORE);

        if (recv1[0] != 101) {
            fprintf(stderr, "rank 1 expected second wait value 101, got %d\n", recv1[0]);
            MPI_Abort(MPI_COMM_WORLD, 3);
        }
    }

    MPI_Finalize();
    return 0;
}

