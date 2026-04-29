#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

static void require_size(int size, int expected, int rank) {
    if (size != expected) {
        if (rank == 0) {
            fprintf(stderr, "test_testall requires %d ranks, got %d\n", expected, size);
        }
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
}

int main(int argc, char **argv) {
    int rank, size;
    int ready = 1;
    int flag = 0;
    int send0 = 800;
    int send1 = 801;
    int recv0[4] = {-1, -1, -1, -1};
    int recv1[4] = {-1, -1, -1, -1};
    MPI_Request reqs[2];

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    require_size(size, 2, rank);

    if (rank == 0) {
        MPI_Recv(&ready, 1, MPI_INT, 1, 82, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        MPI_Send(&send0, 1, MPI_INT, 1, 80, MPI_COMM_WORLD);
        MPI_Send(&send1, 1, MPI_INT, 1, 81, MPI_COMM_WORLD);
    } else {
        MPI_Irecv(recv0, 4, MPI_INT, 0, 80, MPI_COMM_WORLD, &reqs[0]);
        MPI_Irecv(recv1, 4, MPI_INT, 0, 81, MPI_COMM_WORLD, &reqs[1]);

        MPI_Send(&ready, 1, MPI_INT, 0, 82, MPI_COMM_WORLD);

        while (!flag) {
            MPI_Testall(2, reqs, &flag, MPI_STATUSES_IGNORE);
        }

        if (recv0[0] != 800 || recv1[0] != 801) {
            fprintf(stderr, "rank 1 expected values 800 and 801, got %d and %d\n",
                    recv0[0], recv1[0]);
            MPI_Abort(MPI_COMM_WORLD, 2);
        }
    }

    MPI_Finalize();
    return 0;
}

