#include<stdio.h>
#include<stdlib.h>


int main ()
{
	int *ptr;
	printf("ptr default %p\n", ptr);
	printf("%d\n", ptr[0]);
	printf("%d\n", ptr[1]);
	printf("%d\n", ptr[2]);
	printf("%d\n", ptr[3]);
	//free(ptr);   //this will be a terminating call, since memeory on the stack cannot be freed

	ptr = (int*) malloc(3*sizeof(int));
	printf("malloc int %p\n", ptr);
	printf("%d\n", ptr[0]);
	printf("%d\n", ptr[1]);
	printf("%d\n", ptr[2]);
	printf("%d\n", ptr[3]);
	free(ptr);

	ptr = (int*) calloc(1, sizeof(int));
	printf("calloc int 1 %p\n", ptr);
	printf("%d\n", ptr[0]);
	printf("%d\n", ptr[1]);
	printf("%d\n", ptr[2]);
	printf("%d\n", ptr[3]);
	free(ptr);

	ptr = (int*) malloc(0); //gives the last allocated address, if already freed, otherwise gives some other valid address
	//ptr = (int*) calloc(0, sizeof(int));
	printf("malloc 0 %p\n", ptr);
	printf("%d\n", ptr[0]);
	printf("%d\n", ptr[1]);
	printf("%d\n", ptr[2]);
	printf("%d\n", ptr[3]);
	free(ptr);

	ptr = (int*) calloc(0, sizeof(int)); //this always gives some valid address
	//ptr = (int*) malloc(0);
	printf("calloc 0 %p\n", ptr);
	printf("%d\n", ptr[0]);
	printf("%d\n", ptr[1]);
	printf("%d\n", ptr[2]);
	printf("%d\n", ptr[3]);
	free(ptr);

	printf("after free %p\n", ptr);
	printf("%d\n", ptr[0]);
	printf("%d\n", ptr[1]);
	printf("%d\n", ptr[2]);
	printf("%d\n", ptr[3]);
	return 0;
}
