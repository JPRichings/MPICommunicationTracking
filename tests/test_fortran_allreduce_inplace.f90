program test_fortran_allreduce_inplace
  implicit none
  include 'mpif.h'

  integer :: ierr, rank, size, i
  integer :: sendbuf(4)

  call MPI_INIT(ierr)
  call MPI_COMM_RANK(MPI_COMM_WORLD, rank, ierr)
  call MPI_COMM_SIZE(MPI_COMM_WORLD, size, ierr)

  if (size .ne. 4) then
     if (rank .eq. 0) write(*,*) 'test_fortran_allreduce_inplace requires 4 ranks, got ', size
     call MPI_ABORT(MPI_COMM_WORLD, 1, ierr)
  end if

  do i = 1, 4
     sendbuf(i) = rank + i
  end do

  call MPI_ALLREDUCE(MPI_IN_PLACE, sendbuf, 4, MPI_INTEGER, MPI_SUM, MPI_COMM_WORLD, ierr)

  do i = 1, 4
     if (sendbuf(i) .ne. (6 + 4 * i)) then
        write(*,*) 'rank ', rank, ' allreduce inplace mismatch at index ', i, ' value ', sendbuf(i)
        call MPI_ABORT(MPI_COMM_WORLD, 2, ierr)
     end if
  end do

  call MPI_FINALIZE(ierr)
end program test_fortran_allreduce_inplace

