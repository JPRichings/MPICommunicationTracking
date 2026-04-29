#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

static void require_size(int size, int expected, int rank) {
    if (size != expected) {
        if (rank == 0) {
            fprintf(stderr, "test_testsome requires %d ranks, got %d\n", expected, size);
        }
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
}

int main(int argc, char **argv) {
    int rank, size;
    int ready = 1;
    int ack = 1;
    int send0 = 1100;
    int send1 = 1101;
    int send2 = 1102;
    int recv0[4] = {-1, -1, -1, -1};
    int recv1[4] = {-1, -1, -1, -1};
    int recv2[4] = {-1, -1, -1, -1};
    int outcount = 0;
    int indices[3] = {-1, -1, -1};
    int count = -1;
    MPI_Request reqs[3];
    MPI_Status statuses[3];

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    require_size(size, 2, rank);

    if (rank == 0) {
        MPI_Recv(&ready, 1, MPI_INT, 1, 113, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        MPI_Send(&send0, 1, MPI_INT, 1, 110, MPI_COMM_WORLD);
        MPI_Recv(&ack, 1, MPI_INT, 1, 114, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
        MPI_Send(&send1, 1, MPI_INT, 1, 111, MPI_COMM_WORLD);
        MPI_Send(&send2, 1, MPI_INT, 1, 112, MPI_COMM_WORLD);
    } else {
        MPI_Irecv(recv0, 4, MPI_INT, 0, 110, MPI_COMM_WORLD, &reqs[0]);
        MPI_Irecv(recv1, 4, MPI_INT, 0, 111, MPI_COMM_WORLD, &reqs[1]);
        MPI_Irecv(recv2, 4, MPI_INT, 0, 112, MPI_COMM_WORLD, &reqs[2]);

        MPI_Send(&ready, 1, MPI_INT, 0, 113, MPI_COMM_WORLD);

        outcount = 0;
        while (outcount == 0) {
            MPI_Testsome(3, reqs, &outcount, indices, statuses);
        }

        if (outcount != 1 || indices[0] != 0) {
            fprintf(stderr, "rank 1 expected Testsome outcount=1 and indices[0]=0, got outcount=%d index0=%d\n",
                    outcount, indices[0]);
            MPI_Abort(MPI_COMM_WORLD, 2);
        }

        MPI_Get_count(&statuses[0], MPI_INT, &count);
        if (statuses[0].MPI_SOURCE != 0 || count != 1 || recv0[0] != 1100) {
            fprintf(stderr,
                    "rank 1 expected first Testsome completion from rank 0, count 1, value 1100; got source=%d count=%d value=%d\n",
                    statuses[0].MPI_SOURCE, count, recv0[0]);
            MPI_Abort(MPI_COMM_WORLD, 3);
        }

        MPI_Send(&ack, 1, MPI_INT, 0, 114, MPI_COMM_WORLD);

        MPI_Waitall(3, reqs, MPI_STATUSES_IGNORE);

        if (recv1[0] != 1101 || recv2[0] != 1102) {
            fprintf(stderr, "rank 1 expected remaining values 1101 and 1102, got %d and %d\n",
                    recv1[0], recv2[0]);
            MPI_Abort(MPI_COMM_WORLD, 4);
        }
    }

    MPI_Finalize();
    return 0;
}

