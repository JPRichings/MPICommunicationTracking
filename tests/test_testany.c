#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

static void require_size(int size, int expected, int rank) {
    if (size != expected) {
        if (rank == 0) {
            fprintf(stderr, "test_testany requires %d ranks, got %d\n", expected, size);
        }
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
}

int main(int argc, char **argv) {
    int rank, size;
    int ready = 1;
    int ack = 1;
    int flag = 0;
    int send0 = 1000;
    int send1 = 1001;
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
        MPI_Recv(&ready, 1, MPI_INT, 1, 102, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        MPI_Send(&send0, 1, MPI_INT, 1, 100, MPI_COMM_WORLD);
        MPI_Recv(&ack, 1, MPI_INT, 1, 103, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        MPI_Send(&send1, 1, MPI_INT, 1, 101, MPI_COMM_WORLD);
    } else {
        MPI_Irecv(recv0, 4, MPI_INT, 0, 100, MPI_COMM_WORLD, &reqs[0]);
        MPI_Irecv(recv1, 4, MPI_INT, 0, 101, MPI_COMM_WORLD, &reqs[1]);

        MPI_Send(&ready, 1, MPI_INT, 0, 102, MPI_COMM_WORLD);

        while (!flag) {
            MPI_Testany(2, reqs, &index, &flag, &status);
        }

        MPI_Get_count(&status, MPI_INT, &count);
        if (index != 0 || status.MPI_SOURCE != 0 || count != 1 || recv0[0] != 1000) {
            fprintf(stderr,
                    "rank 1 expected Testany to complete index 0 from rank 0, count 1, value 1000; got index=%d source=%d count=%d value=%d\n",
                    index, status.MPI_SOURCE, count, recv0[0]);
            MPI_Abort(MPI_COMM_WORLD, 2);
        }

        MPI_Send(&ack, 1, MPI_INT, 0, 103, MPI_COMM_WORLD);

        MPI_Wait(&reqs[1], MPI_STATUS_IGNORE);

        if (recv1[0] != 1001) {
            fprintf(stderr, "rank 1 expected second value 1001, got %d\n", recv1[0]);
            MPI_Abort(MPI_COMM_WORLD, 3);
        }
    }

    MPI_Finalize();
    return 0;
}

