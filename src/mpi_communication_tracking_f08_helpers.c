#include <stdlib.h>
#include <mpi.h>
#include <ISO_Fortran_binding.h>

void mpi_trace_f08_bcast_helper(CFI_cdesc_t *buf, int count, int datatype_f, int root, int comm_f, int *ierr)
{
    void *base = (buf != NULL) ? buf->base_addr : NULL;

    if (ierr == NULL) return;

    *ierr = (int)MPI_Bcast(base, count, PMPI_Type_f2c((MPI_Fint)datatype_f), root, PMPI_Comm_f2c((MPI_Fint)comm_f));
}

void mpi_trace_f08_reduce_helper(CFI_cdesc_t *sendbuf, CFI_cdesc_t *recvbuf, int count, int datatype_f, int op_f, int root, int comm_f, int *ierr)
{
    const void *s_base = (sendbuf != NULL) ? sendbuf->base_addr : NULL;
    void *r_base = (recvbuf != NULL) ? recvbuf->base_addr : NULL;

    if (ierr == NULL) return;

    *ierr = (int)MPI_Reduce(s_base, r_base, count, PMPI_Type_f2c((MPI_Fint)datatype_f), PMPI_Op_f2c((MPI_Fint)op_f), root, PMPI_Comm_f2c((MPI_Fint)comm_f));
}

void mpi_trace_f08_allreduce_helper(CFI_cdesc_t *sendbuf, CFI_cdesc_t *recvbuf, int count, int datatype_f, int op_f, int comm_f, int *ierr)
{
    const void *s_base = (sendbuf != NULL) ? sendbuf->base_addr : NULL;
    void *r_base = (recvbuf != NULL) ? recvbuf->base_addr : NULL;

    if (ierr == NULL) return;

    *ierr = (int)MPI_Allreduce(s_base, r_base, count, PMPI_Type_f2c((MPI_Fint)datatype_f), PMPI_Op_f2c((MPI_Fint)op_f), PMPI_Comm_f2c((MPI_Fint)comm_f));
}

void mpi_trace_f08_ibcast_helper(CFI_cdesc_t *buf, int count, int datatype_f, int root, int comm_f, int *request_f, int *ierr)
{
    void *base = (buf != NULL) ? buf->base_addr : NULL;
    MPI_Request c_req = MPI_REQUEST_NULL;
    int rc;

    if (ierr == NULL) return;

    rc = (int)MPI_Ibcast(base, count, PMPI_Type_f2c((MPI_Fint)datatype_f), root, PMPI_Comm_f2c((MPI_Fint)comm_f), &c_req);

    if (request_f != NULL) {
        *request_f = (int)PMPI_Request_c2f(c_req);
    }

    *ierr = rc;
}

void mpi_trace_f08_ireduce_helper(CFI_cdesc_t *sendbuf, CFI_cdesc_t *recvbuf, int count, int datatype_f, int op_f, int root, int comm_f, int *request_f, int *ierr)
{
    const void *s_base = (sendbuf != NULL) ? sendbuf->base_addr : NULL;
    void *r_base = (recvbuf != NULL) ? recvbuf->base_addr : NULL;
    MPI_Request c_req = MPI_REQUEST_NULL;
    int rc;

    if (ierr == NULL) return;

    rc = (int)MPI_Ireduce(s_base, r_base, count, PMPI_Type_f2c((MPI_Fint)datatype_f), PMPI_Op_f2c((MPI_Fint)op_f), root, PMPI_Comm_f2c((MPI_Fint)comm_f), &c_req);

    if (request_f != NULL) {
        *request_f = (int)PMPI_Request_c2f(c_req);
    }

    *ierr = rc;
}

void mpi_trace_f08_iallreduce_helper(CFI_cdesc_t *sendbuf, CFI_cdesc_t *recvbuf, int count, int datatype_f, int op_f, int comm_f, int *request_f, int *ierr)
{
    const void *s_base = (sendbuf != NULL) ? sendbuf->base_addr : NULL;
    void *r_base = (recvbuf != NULL) ? recvbuf->base_addr : NULL;
    MPI_Request c_req = MPI_REQUEST_NULL;
    int rc;

    if (ierr == NULL) return;

    rc = (int)MPI_Iallreduce(s_base, r_base, count, PMPI_Type_f2c((MPI_Fint)datatype_f), PMPI_Op_f2c((MPI_Fint)op_f), PMPI_Comm_f2c((MPI_Fint)comm_f), &c_req);

    if (request_f != NULL) {
        *request_f = (int)PMPI_Request_c2f(c_req);
    }

    *ierr = rc;
}

void mpi_trace_f08_send_helper(CFI_cdesc_t *buf, int count, int datatype_f, int dest, int tag, int comm_f, int *ierr)
{
    const void *base = (buf != NULL) ? buf->base_addr : NULL;

    if (ierr == NULL) return;

    *ierr = (int)MPI_Send(base, count, PMPI_Type_f2c((MPI_Fint)datatype_f), dest, tag, MPI_Comm_f2c((MPI_Fint)comm_f));
}

void mpi_trace_f08_recv_helper(CFI_cdesc_t *buf, int count, int datatype_f, int source, int tag, int comm_f, MPI_Status *status, int *ierr)
{
    void *base = (buf != NULL) ? buf->base_addr : NULL;

    if (ierr == NULL) return;

    *ierr = (int)MPI_Recv(base, count, PMPI_Type_f2c((MPI_Fint)datatype_f), source, tag, MPI_Comm_f2c((MPI_Fint)comm_f), status);
}

void mpi_trace_f08_sendrecv_helper(CFI_cdesc_t *sendbuf, int sendcount, int sendtype_f, int dest, int sendtag,
                                   CFI_cdesc_t *recvbuf, int recvcount, int recvtype_f, int source, int recvtag,
                                   int comm_f, MPI_Status *status, int *ierr)
{
    const void *s_base = (sendbuf != NULL) ? sendbuf->base_addr : NULL;
    void *r_base = (recvbuf != NULL) ? recvbuf->base_addr : NULL;

    if (ierr == NULL) return;

    *ierr = (int)MPI_Sendrecv(s_base, sendcount, PMPI_Type_f2c((MPI_Fint)sendtype_f), dest, sendtag,
                              r_base, recvcount, PMPI_Type_f2c((MPI_Fint)recvtype_f), source, recvtag,
                              PMPI_Comm_f2c((MPI_Fint)comm_f), status);
}

void mpi_trace_f08_sendrecv_replace_helper(CFI_cdesc_t *buf, int count, int datatype_f, int dest, int sendtag,
                                           int source, int recvtag, int comm_f, MPI_Status *status, int *ierr)
{
    void *base = (buf != NULL) ? buf->base_addr : NULL;

    if (ierr == NULL) return;

    *ierr = (int)MPI_Sendrecv_replace(base, count, PMPI_Type_f2c((MPI_Fint)datatype_f), dest, sendtag,
                                      source, recvtag, PMPI_Comm_f2c((MPI_Fint)comm_f), status);
}

void mpi_trace_f08_irecv_helper(CFI_cdesc_t *buf, int count, int datatype_f, int source, int tag, int comm_f, int *request_f, int *ierr)
{
    void *base = (buf != NULL) ? buf->base_addr : NULL;
    MPI_Request c_req = MPI_REQUEST_NULL;
    int rc;

    if (ierr == NULL) return;

    rc = (int)MPI_Irecv(base, count, PMPI_Type_f2c((MPI_Fint)datatype_f), source, tag, MPI_Comm_f2c((MPI_Fint)comm_f), &c_req);

    if (request_f != NULL) {
        *request_f = (int)PMPI_Request_c2f(c_req);
    }

    *ierr = rc;
}

void mpi_trace_f08_wait_helper(int *request_f, MPI_Status *status, int *ierr)
{
    MPI_Request c_req = MPI_REQUEST_NULL;
    int rc;

    if (ierr == NULL) return;

    if (request_f != NULL) {
        c_req = PMPI_Request_f2c((MPI_Fint)*request_f);
    }

    rc = (int)MPI_Wait(&c_req, status);

    if (request_f != NULL) {
        *request_f = (int)PMPI_Request_c2f(c_req);
    }

    *ierr = rc;
}

void mpi_trace_f08_isend_helper(CFI_cdesc_t *buf, int count, int datatype_f, int dest, int tag, int comm_f, int *request_f, int *ierr)
{
    const void *base = (buf != NULL) ? buf->base_addr : NULL;
    MPI_Request c_req = MPI_REQUEST_NULL;
    int rc;

    if (ierr == NULL) return;

    rc = (int)MPI_Isend(base, count, PMPI_Type_f2c((MPI_Fint)datatype_f), dest, tag, MPI_Comm_f2c((MPI_Fint)comm_f), &c_req);

    if (request_f != NULL) {
        *request_f = (int)PMPI_Request_c2f(c_req);
    }

    *ierr = rc;
}

void mpi_trace_f08_waitall_helper(int count, int request_f[], MPI_Status statuses[], int *ierr)
{
    int i;
    MPI_Request *c_requests = NULL;
    int rc;

    if (ierr == NULL) return;

    if (count < 0) {
        *ierr = MPI_ERR_ARG;
        return;
    }

    if (count == 0) {
        *ierr = (int)MPI_Waitall(0, NULL, statuses);
        return;
    }

    c_requests = (MPI_Request *)malloc((size_t)count * sizeof(MPI_Request));
    if (c_requests == NULL) {
        *ierr = MPI_ERR_NO_MEM;
        return;
    }

    for (i = 0; i < count; i++) {
        c_requests[i] = PMPI_Request_f2c((MPI_Fint)request_f[i]);
    }

    rc = (int)MPI_Waitall(count, c_requests, statuses);

    for (i = 0; i < count; i++) {
        request_f[i] = (int)PMPI_Request_c2f(c_requests[i]);
    }

    free(c_requests);
    *ierr = rc;
}

void mpi_trace_f08_waitany_helper(int count, int request_f[], int *index_c, MPI_Status *status, int *ierr)
{
    int i;
    int rc;
    int c_index = MPI_UNDEFINED;
    MPI_Request *c_requests = NULL;

    if (ierr == NULL) return;

    if (count < 0) {
        *ierr = MPI_ERR_ARG;
        return;
    }

    if (count > 0) {
        c_requests = (MPI_Request *)malloc((size_t)count * sizeof(MPI_Request));
        if (c_requests == NULL) {
            *ierr = MPI_ERR_NO_MEM;
            return;
        }

        for (i = 0; i < count; i++) {
            c_requests[i] = PMPI_Request_f2c((MPI_Fint)request_f[i]);
        }
    }

    rc = (int)MPI_Waitany(count, c_requests, &c_index, status);

    if (count > 0) {
        for (i = 0; i < count; i++) {
            request_f[i] = (int)PMPI_Request_c2f(c_requests[i]);
        }
    }

    if (index_c != NULL) {
        *index_c = c_index;
    }

    free(c_requests);
    *ierr = rc;
}

void mpi_trace_f08_testall_helper(int count, int request_f[], int *flag_c, MPI_Status statuses[], int *ierr)
{
    int i;
    int rc;
    int c_flag = 0;
    MPI_Request *c_requests = NULL;

    if (ierr == NULL) return;

    if (count < 0) {
        *ierr = MPI_ERR_ARG;
        return;
    }

    if (count > 0) {
        c_requests = (MPI_Request *)malloc((size_t)count * sizeof(MPI_Request));
        if (c_requests == NULL) {
            *ierr = MPI_ERR_NO_MEM;
            return;
        }

        for (i = 0; i < count; i++) {
            c_requests[i] = PMPI_Request_f2c((MPI_Fint)request_f[i]);
        }
    }

    rc = (int)MPI_Testall(count, c_requests, &c_flag, statuses);

    if (count > 0) {
        for (i = 0; i < count; i++) {
            request_f[i] = (int)PMPI_Request_c2f(c_requests[i]);
        }
    }

    if (flag_c != NULL) {
        *flag_c = c_flag;
    }

    free(c_requests);
    *ierr = rc;
}

/* ========================================================================== */
/* F08 C Helpers: WAIT/TEST COMPLETION FAMILY                                 */
/* ========================================================================== */

void mpi_trace_f08_waitsome_helper(int incount, int request_f[], int *outcount_c, int indices_c[], MPI_Status statuses[], int *ierr) {
    int i;
    int rc;
    int c_outcount = MPI_UNDEFINED;
    MPI_Request *c_requests = NULL;

    if (ierr == NULL) return;
    if (incount < 0) { *ierr = MPI_ERR_ARG; return; }

    if (incount > 0) {
        c_requests = (MPI_Request *)malloc((size_t)incount * sizeof(MPI_Request));
        for (i = 0; i < incount; i++) c_requests[i] = PMPI_Request_f2c((MPI_Fint)request_f[i]);
    }

    rc = (int)MPI_Waitsome(incount, c_requests, &c_outcount, indices_c, statuses);

    if (incount > 0) {
        for (i = 0; i < incount; i++) request_f[i] = (int)PMPI_Request_c2f(c_requests[i]);
    }
    if (outcount_c != NULL) *outcount_c = c_outcount;

    free(c_requests);
    *ierr = rc;
}

void mpi_trace_f08_test_helper(int *request_f, int *flag_c, MPI_Status *status, int *ierr) {
    MPI_Request c_req = MPI_REQUEST_NULL;
    int c_flag = 0;
    int rc;

    if (ierr == NULL) return;
    if (request_f != NULL) c_req = PMPI_Request_f2c((MPI_Fint)*request_f);

    rc = (int)MPI_Test(&c_req, &c_flag, status);

    if (request_f != NULL) *request_f = (int)PMPI_Request_c2f(c_req);
    if (flag_c != NULL) *flag_c = c_flag;
    
    *ierr = rc;
}

void mpi_trace_f08_testany_helper(int count, int request_f[], int *index_c, int *flag_c, MPI_Status *status, int *ierr) {
    int i;
    int rc;
    int c_index = MPI_UNDEFINED;
    int c_flag = 0;
    MPI_Request *c_requests = NULL;

    if (ierr == NULL) return;
    if (count < 0) { *ierr = MPI_ERR_ARG; return; }

    if (count > 0) {
        c_requests = (MPI_Request *)malloc((size_t)count * sizeof(MPI_Request));
        for (i = 0; i < count; i++) c_requests[i] = PMPI_Request_f2c((MPI_Fint)request_f[i]);
    }

    rc = (int)MPI_Testany(count, c_requests, &c_index, &c_flag, status);

    if (count > 0) {
        for (i = 0; i < count; i++) request_f[i] = (int)PMPI_Request_c2f(c_requests[i]);
    }
    if (index_c != NULL) *index_c = c_index;
    if (flag_c != NULL) *flag_c = c_flag;

    free(c_requests);
    *ierr = rc;
}

void mpi_trace_f08_testsome_helper(int incount, int request_f[], int *outcount_c, int indices_c[], MPI_Status statuses[], int *ierr) {
    int i;
    int rc;
    int c_outcount = MPI_UNDEFINED;
    MPI_Request *c_requests = NULL;

    if (ierr == NULL) return;
    if (incount < 0) { *ierr = MPI_ERR_ARG; return; }

    if (incount > 0) {
        c_requests = (MPI_Request *)malloc((size_t)incount * sizeof(MPI_Request));
        for (i = 0; i < incount; i++) c_requests[i] = PMPI_Request_f2c((MPI_Fint)request_f[i]);
    }

    rc = (int)MPI_Testsome(incount, c_requests, &c_outcount, indices_c, statuses);

    if (incount > 0) {
        for (i = 0; i < incount; i++) request_f[i] = (int)PMPI_Request_c2f(c_requests[i]);
    }
    if (outcount_c != NULL) *outcount_c = c_outcount;

    free(c_requests);
    *ierr = rc;
}

void mpi_trace_f08_barrier_helper(int comm_f, int *ierr)
{
    if (ierr == NULL) return;
    *ierr = (int)MPI_Barrier(MPI_Comm_f2c((MPI_Fint)comm_f));
}

void mpi_trace_f08_cancel_helper(int *request_f, int *ierr)
{
    MPI_Request c_req = MPI_REQUEST_NULL;
    int rc;

    if (ierr == NULL) return;

    if (request_f != NULL) {
        c_req = PMPI_Request_f2c((MPI_Fint)*request_f);
    }

    rc = (int)MPI_Cancel(&c_req);

    if (request_f != NULL) {
        *request_f = (int)PMPI_Request_c2f(c_req);
    }

    *ierr = rc;
}

