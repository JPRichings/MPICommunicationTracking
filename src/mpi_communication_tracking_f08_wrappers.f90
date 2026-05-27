subroutine mpi_bcast_f08ts(buf, count, datatype, root, comm, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Datatype, MPI_Comm
  implicit none

  type(*), dimension(..) :: buf
  integer, intent(in) :: count, root
  type(MPI_Datatype), intent(in) :: datatype
  type(MPI_Comm), intent(in) :: comm
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c

  interface
    subroutine mpi_trace_f08_bcast_helper(buf, count, datatype_f, root, comm_f, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      type(*), dimension(..) :: buf
      integer(c_int), value :: count, datatype_f, root, comm_f
      integer(c_int) :: ierr
    end subroutine
  end interface

  call mpi_trace_f08_bcast_helper(buf, int(count, c_int), int(datatype%MPI_VAL, c_int), int(root, c_int), int(comm%MPI_VAL, c_int), ierr_c)

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_bcast_f08ts

subroutine mpi_reduce_f08ts(sendbuf, recvbuf, count, datatype, op, root, comm, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Datatype, MPI_Op, MPI_Comm
  implicit none

  type(*), dimension(..), intent(in) :: sendbuf
  type(*), dimension(..) :: recvbuf
  integer, intent(in) :: count, root
  type(MPI_Datatype), intent(in) :: datatype
  type(MPI_Op), intent(in) :: op
  type(MPI_Comm), intent(in) :: comm
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c

  interface
    subroutine mpi_trace_f08_reduce_helper(sendbuf, recvbuf, count, datatype_f, op_f, root, comm_f, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      type(*), dimension(..), intent(in) :: sendbuf
      type(*), dimension(..) :: recvbuf
      integer(c_int), value :: count, datatype_f, op_f, root, comm_f
      integer(c_int) :: ierr
    end subroutine
  end interface

  call mpi_trace_f08_reduce_helper(sendbuf, recvbuf, int(count, c_int), int(datatype%MPI_VAL, c_int), int(op%MPI_VAL, c_int), int(root, c_int), int(comm%MPI_VAL, c_int), ierr_c)

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_reduce_f08ts

subroutine mpi_allreduce_f08ts(sendbuf, recvbuf, count, datatype, op, comm, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Datatype, MPI_Op, MPI_Comm
  implicit none

  type(*), dimension(..), intent(in) :: sendbuf
  type(*), dimension(..) :: recvbuf
  integer, intent(in) :: count
  type(MPI_Datatype), intent(in) :: datatype
  type(MPI_Op), intent(in) :: op
  type(MPI_Comm), intent(in) :: comm
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c

  interface
    subroutine mpi_trace_f08_allreduce_helper(sendbuf, recvbuf, count, datatype_f, op_f, comm_f, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      type(*), dimension(..), intent(in) :: sendbuf
      type(*), dimension(..) :: recvbuf
      integer(c_int), value :: count, datatype_f, op_f, comm_f
      integer(c_int) :: ierr
    end subroutine
  end interface

  call mpi_trace_f08_allreduce_helper(sendbuf, recvbuf, int(count, c_int), int(datatype%MPI_VAL, c_int), int(op%MPI_VAL, c_int), int(comm%MPI_VAL, c_int), ierr_c)

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_allreduce_f08ts

subroutine mpi_ibcast_f08ts(buf, count, datatype, root, comm, request, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Datatype, MPI_Comm, MPI_Request
  implicit none

  type(*), dimension(..), asynchronous :: buf
  integer, intent(in) :: count, root
  type(MPI_Datatype), intent(in) :: datatype
  type(MPI_Comm), intent(in) :: comm
  type(MPI_Request), intent(out) :: request
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c
  integer(c_int) :: request_f_c

  interface
    subroutine mpi_trace_f08_ibcast_helper(buf, count, datatype_f, root, comm_f, request_f, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      type(*), dimension(..), asynchronous :: buf
      integer(c_int), value :: count, datatype_f, root, comm_f
      integer(c_int) :: request_f
      integer(c_int) :: ierr
    end subroutine
  end interface

  call mpi_trace_f08_ibcast_helper(buf, int(count, c_int), int(datatype%MPI_VAL, c_int), int(root, c_int), int(comm%MPI_VAL, c_int), request_f_c, ierr_c)
  
  request%MPI_VAL = request_f_c
  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_ibcast_f08ts


subroutine mpi_ireduce_f08ts(sendbuf, recvbuf, count, datatype, op, root, comm, request, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Datatype, MPI_Op, MPI_Comm, MPI_Request
  implicit none

  type(*), dimension(..), asynchronous, intent(in) :: sendbuf
  type(*), dimension(..), asynchronous :: recvbuf
  integer, intent(in) :: count, root
  type(MPI_Datatype), intent(in) :: datatype
  type(MPI_Op), intent(in) :: op
  type(MPI_Comm), intent(in) :: comm
  type(MPI_Request), intent(out) :: request
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c
  integer(c_int) :: request_f_c

  interface
    subroutine mpi_trace_f08_ireduce_helper(sendbuf, recvbuf, count, datatype_f, op_f, root, comm_f, request_f, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      type(*), dimension(..), asynchronous, intent(in) :: sendbuf
      type(*), dimension(..), asynchronous :: recvbuf
      integer(c_int), value :: count, datatype_f, op_f, root, comm_f
      integer(c_int) :: request_f
      integer(c_int) :: ierr
    end subroutine
  end interface

  call mpi_trace_f08_ireduce_helper(sendbuf, recvbuf, int(count, c_int), int(datatype%MPI_VAL, c_int), int(op%MPI_VAL, c_int), int(root, c_int), int(comm%MPI_VAL, c_int), request_f_c, ierr_c)

  request%MPI_VAL = request_f_c
  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_ireduce_f08ts


subroutine mpi_iallreduce_f08ts(sendbuf, recvbuf, count, datatype, op, comm, request, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Datatype, MPI_Op, MPI_Comm, MPI_Request
  implicit none

  type(*), dimension(..), asynchronous, intent(in) :: sendbuf
  type(*), dimension(..), asynchronous :: recvbuf
  integer, intent(in) :: count
  type(MPI_Datatype), intent(in) :: datatype
  type(MPI_Op), intent(in) :: op
  type(MPI_Comm), intent(in) :: comm
  type(MPI_Request), intent(out) :: request
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c
  integer(c_int) :: request_f_c

  interface
    subroutine mpi_trace_f08_iallreduce_helper(sendbuf, recvbuf, count, datatype_f, op_f, comm_f, request_f, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      type(*), dimension(..), asynchronous, intent(in) :: sendbuf
      type(*), dimension(..), asynchronous :: recvbuf
      integer(c_int), value :: count, datatype_f, op_f, comm_f
      integer(c_int) :: request_f
      integer(c_int) :: ierr
    end subroutine
  end interface

  call mpi_trace_f08_iallreduce_helper(sendbuf, recvbuf, int(count, c_int), int(datatype%MPI_VAL, c_int), int(op%MPI_VAL, c_int), int(comm%MPI_VAL, c_int), request_f_c, ierr_c)

  request%MPI_VAL = request_f_c
  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_iallreduce_f08ts

subroutine mpi_send_f08ts(buf, count, datatype, dest, tag, comm, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Datatype, MPI_Comm
  implicit none

  type(*), dimension(..), intent(in) :: buf
  integer, intent(in) :: count, dest, tag
  type(MPI_Datatype), intent(in) :: datatype
  type(MPI_Comm), intent(in) :: comm
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c

  interface
    subroutine mpi_trace_f08_send_helper(buf, count, datatype_f, dest, tag, comm_f, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      type(*), dimension(..), intent(in) :: buf
      integer(c_int), value :: count, datatype_f, dest, tag, comm_f
      integer(c_int) :: ierr
    end subroutine
  end interface

  call mpi_trace_f08_send_helper(buf, int(count, c_int), int(datatype%MPI_VAL, c_int), int(dest, c_int), int(tag, c_int), int(comm%MPI_VAL, c_int), ierr_c)

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_send_f08ts


subroutine mpi_recv_f08ts(buf, count, datatype, source, tag, comm, status, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Datatype, MPI_Comm, MPI_Status
  implicit none

  type(*), dimension(..) :: buf
  integer, intent(in) :: count, source, tag
  type(MPI_Datatype), intent(in) :: datatype
  type(MPI_Comm), intent(in) :: comm
  type(MPI_Status), intent(out) :: status
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c

  interface
    subroutine mpi_trace_f08_recv_helper(buf, count, datatype_f, source, tag, comm_f, status, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      use mpi_f08, only : MPI_Status
      type(*), dimension(..) :: buf
      integer(c_int), value :: count, datatype_f, source, tag, comm_f
      type(MPI_Status) :: status
      integer(c_int) :: ierr
    end subroutine
  end interface

  call mpi_trace_f08_recv_helper(buf, int(count, c_int), int(datatype%MPI_VAL, c_int), int(source, c_int), int(tag, c_int), int(comm%MPI_VAL, c_int), status, ierr_c)

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_recv_f08ts

subroutine mpi_sendrecv_f08ts(sendbuf, sendcount, sendtype, dest, sendtag, &
                              recvbuf, recvcount, recvtype, source, recvtag, &
                              comm, status, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Datatype, MPI_Comm, MPI_Status
  implicit none

  type(*), dimension(..), intent(in) :: sendbuf
  type(*), dimension(..) :: recvbuf
  integer, intent(in) :: sendcount, dest, sendtag
  integer, intent(in) :: recvcount, source, recvtag
  type(MPI_Datatype), intent(in) :: sendtype, recvtype
  type(MPI_Comm), intent(in) :: comm
  type(MPI_Status), intent(out) :: status
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c

  interface
    subroutine mpi_trace_f08_sendrecv_helper(sendbuf, sendcount, sendtype_f, dest, sendtag, &
                                             recvbuf, recvcount, recvtype_f, source, recvtag, &
                                             comm_f, status, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      use mpi_f08, only : MPI_Status
      type(*), dimension(..), intent(in) :: sendbuf
      type(*), dimension(..) :: recvbuf
      integer(c_int), value :: sendcount, sendtype_f, dest, sendtag
      integer(c_int), value :: recvcount, recvtype_f, source, recvtag, comm_f
      type(MPI_Status) :: status
      integer(c_int) :: ierr
    end subroutine
  end interface

  call mpi_trace_f08_sendrecv_helper(sendbuf, int(sendcount, c_int), int(sendtype%MPI_VAL, c_int), int(dest, c_int), int(sendtag, c_int), &
                                     recvbuf, int(recvcount, c_int), int(recvtype%MPI_VAL, c_int), int(source, c_int), int(recvtag, c_int), &
                                     int(comm%MPI_VAL, c_int), status, ierr_c)

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_sendrecv_f08ts

subroutine mpi_sendrecv_replace_f08ts(buf, count, datatype, dest, sendtag, source, recvtag, comm, status, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Datatype, MPI_Comm, MPI_Status
  implicit none

  type(*), dimension(..) :: buf
  integer, intent(in) :: count, dest, sendtag, source, recvtag
  type(MPI_Datatype), intent(in) :: datatype
  type(MPI_Comm), intent(in) :: comm
  type(MPI_Status), intent(out) :: status
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c

  interface
    subroutine mpi_trace_f08_sendrecv_replace_helper(buf, count, datatype_f, dest, sendtag, source, recvtag, comm_f, status, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      use mpi_f08, only : MPI_Status
      type(*), dimension(..) :: buf
      integer(c_int), value :: count, datatype_f, dest, sendtag, source, recvtag, comm_f
      type(MPI_Status) :: status
      integer(c_int) :: ierr
    end subroutine
  end interface

  call mpi_trace_f08_sendrecv_replace_helper(buf, int(count, c_int), int(datatype%MPI_VAL, c_int), int(dest, c_int), int(sendtag, c_int), &
                                             int(source, c_int), int(recvtag, c_int), int(comm%MPI_VAL, c_int), status, ierr_c)

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_sendrecv_replace_f08ts

subroutine mpi_irecv_f08ts(buf, count, datatype, source, tag, comm, request, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Datatype, MPI_Comm, MPI_Request
  implicit none

  type(*), dimension(..), asynchronous :: buf
  integer, intent(in) :: count, source, tag
  type(MPI_Datatype), intent(in) :: datatype
  type(MPI_Comm), intent(in) :: comm
  type(MPI_Request), intent(out) :: request
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c
  integer(c_int) :: request_f_c

  interface
    subroutine mpi_trace_f08_irecv_helper(buf, count, datatype_f, source, tag, comm_f, request_f, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      type(*), dimension(..), asynchronous :: buf
      integer(c_int), value :: count, datatype_f, source, tag, comm_f
      integer(c_int) :: request_f
      integer(c_int) :: ierr
    end subroutine
  end interface

  call mpi_trace_f08_irecv_helper(buf, int(count, c_int), int(datatype%MPI_VAL, c_int), int(source, c_int), int(tag, c_int), int(comm%MPI_VAL, c_int), request_f_c, ierr_c)

  request%MPI_VAL = request_f_c

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_irecv_f08ts


subroutine mpi_wait_f08(request, status, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Request, MPI_Status
  implicit none

  type(MPI_Request), intent(inout) :: request
  type(MPI_Status), intent(out) :: status
  integer, optional, intent(out) :: ierror

  integer(c_int) :: request_f_c
  integer(c_int) :: ierr_c

  interface
    subroutine mpi_trace_f08_wait_helper(request_f, status, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      use mpi_f08, only : MPI_Status
      integer(c_int) :: request_f
      type(MPI_Status) :: status
      integer(c_int) :: ierr
    end subroutine
  end interface

  request_f_c = request%MPI_VAL

  call mpi_trace_f08_wait_helper(request_f_c, status, ierr_c)

  request%MPI_VAL = request_f_c

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_wait_f08

subroutine mpi_isend_f08ts(buf, count, datatype, dest, tag, comm, request, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Datatype, MPI_Comm, MPI_Request
  implicit none

  type(*), dimension(..), asynchronous :: buf
  integer, intent(in) :: count, dest, tag
  type(MPI_Datatype), intent(in) :: datatype
  type(MPI_Comm), intent(in) :: comm
  type(MPI_Request), intent(out) :: request
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c
  integer(c_int) :: request_f_c

  interface
    subroutine mpi_trace_f08_isend_helper(buf, count, datatype_f, dest, tag, comm_f, request_f, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      type(*), dimension(..), asynchronous :: buf
      integer(c_int), value :: count, datatype_f, dest, tag, comm_f
      integer(c_int) :: request_f
      integer(c_int) :: ierr
    end subroutine
  end interface

  call mpi_trace_f08_isend_helper(buf, int(count, c_int), int(datatype%MPI_VAL, c_int), int(dest, c_int), int(tag, c_int), int(comm%MPI_VAL, c_int), request_f_c, ierr_c)

  request%MPI_VAL = request_f_c

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_isend_f08ts

subroutine mpi_waitall_f08(count, array_of_requests, array_of_statuses, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Request, MPI_Status
  implicit none

  integer, intent(in) :: count
  type(MPI_Request), intent(inout) :: array_of_requests(count)
  type(MPI_Status), intent(out) :: array_of_statuses(count)
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c
  integer(c_int) :: request_f_c(count)
  integer :: i

  interface
    subroutine mpi_trace_f08_waitall_helper(count, request_f, statuses, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      use mpi_f08, only : MPI_Status
      integer(c_int), value :: count
      integer(c_int) :: request_f(*)
      type(MPI_Status) :: statuses(*)
      integer(c_int) :: ierr
    end subroutine
  end interface

  do i = 1, count
     request_f_c(i) = array_of_requests(i)%MPI_VAL
  end do

  call mpi_trace_f08_waitall_helper(int(count, c_int), request_f_c, array_of_statuses, ierr_c)

  do i = 1, count
     array_of_requests(i)%MPI_VAL = request_f_c(i)
  end do

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_waitall_f08

subroutine mpi_waitany_f08(count, array_of_requests, index, status, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Request, MPI_Status, MPI_UNDEFINED
  implicit none

  integer, intent(in) :: count
  type(MPI_Request), intent(inout) :: array_of_requests(count)
  integer, intent(out) :: index
  type(MPI_Status), intent(out) :: status
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c
  integer(c_int) :: index_c
  integer(c_int) :: request_f_c(count)
  integer :: i

  interface
    subroutine mpi_trace_f08_waitany_helper(count, request_f, index_c, status, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      use mpi_f08, only : MPI_Status
      integer(c_int), value :: count
      integer(c_int) :: request_f(*)
      integer(c_int) :: index_c
      type(MPI_Status) :: status
      integer(c_int) :: ierr
    end subroutine
  end interface

  do i = 1, count
     request_f_c(i) = array_of_requests(i)%MPI_VAL
  end do

  call mpi_trace_f08_waitany_helper(int(count, c_int), request_f_c, index_c, status, ierr_c)

  do i = 1, count
     array_of_requests(i)%MPI_VAL = request_f_c(i)
  end do

  if (index_c == int(MPI_UNDEFINED, c_int)) then
     index = MPI_UNDEFINED
  else
     index = int(index_c) + 1
  end if

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_waitany_f08


subroutine mpi_testall_f08(count, array_of_requests, flag, array_of_statuses, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Request, MPI_Status
  implicit none

  integer, intent(in) :: count
  type(MPI_Request), intent(inout) :: array_of_requests(count)
  logical, intent(out) :: flag
  type(MPI_Status), intent(out) :: array_of_statuses(count)
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c
  integer(c_int) :: flag_c
  integer(c_int) :: request_f_c(count)
  integer :: i

  interface
    subroutine mpi_trace_f08_testall_helper(count, request_f, flag_c, statuses, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      use mpi_f08, only : MPI_Status
      integer(c_int), value :: count
      integer(c_int) :: request_f(*)
      integer(c_int) :: flag_c
      type(MPI_Status) :: statuses(*)
      integer(c_int) :: ierr
    end subroutine
  end interface

  do i = 1, count
     request_f_c(i) = array_of_requests(i)%MPI_VAL
  end do

  call mpi_trace_f08_testall_helper(int(count, c_int), request_f_c, flag_c, array_of_statuses, ierr_c)

  do i = 1, count
     array_of_requests(i)%MPI_VAL = request_f_c(i)
  end do

  flag = (flag_c /= 0_c_int)

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_testall_f08

subroutine mpi_waitsome_f08(incount, array_of_requests, outcount, array_of_indices, array_of_statuses, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Request, MPI_Status, MPI_UNDEFINED
  implicit none

  integer, intent(in) :: incount
  type(MPI_Request), intent(inout) :: array_of_requests(incount)
  integer, intent(out) :: outcount
  integer, intent(out) :: array_of_indices(*)
  type(MPI_Status), intent(out) :: array_of_statuses(*)
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c, outcount_c
  integer(c_int) :: request_f_c(incount)
  integer(c_int) :: indices_c(incount)
  integer :: i

  interface
    subroutine mpi_trace_f08_waitsome_helper(incount, request_f, outcount_c, indices_c, statuses, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      use mpi_f08, only : MPI_Status
      integer(c_int), value :: incount
      integer(c_int) :: request_f(*)
      integer(c_int) :: outcount_c
      integer(c_int) :: indices_c(*)
      type(MPI_Status) :: statuses(*)
      integer(c_int) :: ierr
    end subroutine
  end interface

  if (incount > 0) then
      do i = 1, incount
          request_f_c(i) = array_of_requests(i)%MPI_VAL
      end do
  end if

  call mpi_trace_f08_waitsome_helper(int(incount, c_int), request_f_c, outcount_c, indices_c, array_of_statuses, ierr_c)

  if (incount > 0) then
      do i = 1, incount
          array_of_requests(i)%MPI_VAL = request_f_c(i)
      end do
  end if

  outcount = int(outcount_c)
  if (outcount /= MPI_UNDEFINED) then
      do i = 1, outcount
          ! Translate C 0-based index to Fortran 1-based index
          array_of_indices(i) = int(indices_c(i)) + 1
      end do
  end if

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_waitsome_f08

subroutine mpi_test_f08(request, flag, status, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Request, MPI_Status
  implicit none

  type(MPI_Request), intent(inout) :: request
  logical, intent(out) :: flag
  type(MPI_Status), intent(out) :: status
  integer, optional, intent(out) :: ierror

  integer(c_int) :: request_f_c
  integer(c_int) :: flag_c, ierr_c

  interface
    subroutine mpi_trace_f08_test_helper(request_f, flag_c, status, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      use mpi_f08, only : MPI_Status
      integer(c_int) :: request_f
      integer(c_int) :: flag_c
      type(MPI_Status) :: status
      integer(c_int) :: ierr
    end subroutine
  end interface

  request_f_c = request%MPI_VAL

  call mpi_trace_f08_test_helper(request_f_c, flag_c, status, ierr_c)

  request%MPI_VAL = request_f_c
  flag = (flag_c /= 0_c_int)

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_test_f08

subroutine mpi_testany_f08(count, array_of_requests, index, flag, status, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Request, MPI_Status, MPI_UNDEFINED
  implicit none

  integer, intent(in) :: count
  type(MPI_Request), intent(inout) :: array_of_requests(count)
  integer, intent(out) :: index
  logical, intent(out) :: flag
  type(MPI_Status), intent(out) :: status
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c, index_c, flag_c
  integer(c_int) :: request_f_c(count)
  integer :: i

  interface
    subroutine mpi_trace_f08_testany_helper(count, request_f, index_c, flag_c, status, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      use mpi_f08, only : MPI_Status
      integer(c_int), value :: count
      integer(c_int) :: request_f(*)
      integer(c_int) :: index_c, flag_c
      type(MPI_Status) :: status
      integer(c_int) :: ierr
    end subroutine
  end interface

  if (count > 0) then
      do i = 1, count
          request_f_c(i) = array_of_requests(i)%MPI_VAL
      end do
  end if

  call mpi_trace_f08_testany_helper(int(count, c_int), request_f_c, index_c, flag_c, status, ierr_c)

  if (count > 0) then
      do i = 1, count
          array_of_requests(i)%MPI_VAL = request_f_c(i)
      end do
  end if

  flag = (flag_c /= 0_c_int)
  if (index_c == int(MPI_UNDEFINED, c_int)) then
      index = MPI_UNDEFINED
  else
      index = int(index_c) + 1
  end if

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_testany_f08

subroutine mpi_testsome_f08(incount, array_of_requests, outcount, array_of_indices, array_of_statuses, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Request, MPI_Status, MPI_UNDEFINED
  implicit none

  integer, intent(in) :: incount
  type(MPI_Request), intent(inout) :: array_of_requests(incount)
  integer, intent(out) :: outcount
  integer, intent(out) :: array_of_indices(*)
  type(MPI_Status), intent(out) :: array_of_statuses(*)
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c, outcount_c
  integer(c_int) :: request_f_c(incount)
  integer(c_int) :: indices_c(incount)
  integer :: i

  interface
    subroutine mpi_trace_f08_testsome_helper(incount, request_f, outcount_c, indices_c, statuses, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      use mpi_f08, only : MPI_Status
      integer(c_int), value :: incount
      integer(c_int) :: request_f(*)
      integer(c_int) :: outcount_c
      integer(c_int) :: indices_c(*)
      type(MPI_Status) :: statuses(*)
      integer(c_int) :: ierr
    end subroutine
  end interface

  if (incount > 0) then
      do i = 1, incount
          request_f_c(i) = array_of_requests(i)%MPI_VAL
      end do
  end if

  call mpi_trace_f08_testsome_helper(int(incount, c_int), request_f_c, outcount_c, indices_c, array_of_statuses, ierr_c)

  if (incount > 0) then
      do i = 1, incount
          array_of_requests(i)%MPI_VAL = request_f_c(i)
      end do
  end if

  outcount = int(outcount_c)
  if (outcount /= MPI_UNDEFINED) then
      do i = 1, outcount
          array_of_indices(i) = int(indices_c(i)) + 1
      end do
  end if

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_testsome_f08

subroutine mpi_barrier_f08(comm, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Comm
  implicit none

  type(MPI_Comm), intent(in) :: comm
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c

  interface
    subroutine mpi_trace_f08_barrier_helper(comm_f, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      integer(c_int), value :: comm_f
      integer(c_int) :: ierr
    end subroutine
  end interface

  call mpi_trace_f08_barrier_helper(int(comm%MPI_VAL, c_int), ierr_c)

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_barrier_f08


subroutine mpi_cancel_f08(request, ierror)
  use, intrinsic :: iso_c_binding, only : c_int
  use mpi_f08, only : MPI_Request
  implicit none

  type(MPI_Request), intent(inout) :: request
  integer, optional, intent(out) :: ierror

  integer(c_int) :: ierr_c
  integer(c_int) :: request_f_c

  interface
    subroutine mpi_trace_f08_cancel_helper(request_f, ierr) bind(C)
      use, intrinsic :: iso_c_binding, only : c_int
      integer(c_int) :: request_f
      integer(c_int) :: ierr
    end subroutine
  end interface

  request_f_c = request%MPI_VAL

  call mpi_trace_f08_cancel_helper(request_f_c, ierr_c)

  request%MPI_VAL = request_f_c

  if (present(ierror)) ierror = int(ierr_c)
end subroutine mpi_cancel_f08

