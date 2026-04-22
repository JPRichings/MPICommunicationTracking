program pingpong
  use mpi_f08

  implicit none
  integer:: ierr
  integer :: rank, world_size, length
  character(MPI_MAX_PROCESSOR_NAME) :: hostname

  real(kind=8):: data = 0.d0 
  type(MPI_STATUS):: status

  call mpi_init(ierr)

  call mpi_comm_rank(MPI_COMM_WORLD, rank, ierr)
  call mpi_comm_size(MPI_COMM_WORLD, world_size, ierr)
  call mpi_get_processor_name(hostname, length, ierr)
  write(*,*) "Hi, I'm ",rank," on ",hostname

  if(rank==0) data = 1.d0
  if(rank==1) data = 2.d0

  if(rank==0) then
     call mpi_send(data, 1, MPI_DOUBLE_PRECISION, 1, 0, MPI_COMM_WORLD, ierr)
     call mpi_recv(data, 1, MPI_DOUBLE_PRECISION, 1, 0, MPI_COMM_WORLD, status, ierr)
  else if(rank==1) then
     call mpi_recv(data, 1, MPI_DOUBLE_PRECISION, 0, 0, MPI_COMM_WORLD, status, ierr)
     call mpi_send(data, 1, MPI_DOUBLE_PRECISION, 0, 0, MPI_COMM_WORLD, ierr)
  endif

  call mpi_finalize(ierr)

end program pingpong

