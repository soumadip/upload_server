#include<stdio.h>

int main ()
{
	int a=10; int *ptr; //this is an integer type pointer

	printf ("value of the int variable a: %d\n", a);     //  10 
	printf ("value of pointer variable ptr (garbage): %d\n", ptr);  //   <some garbage value>
	printf ("value of pointer the variable ptr (garbade) in the form of memory address: %p\n", ptr);  //   <the same garbage value in the form of an memory address>  
	printf ("memory address of the pointer variable ptr: %p\n", &ptr); //   the address of the variable ptr
	printf ("memory address of the int variable a: %p\n", &a);   //   memory address of the variable a 
	ptr = &a;            //stores the address of a on ptr
	printf ("value of the pointer variable ptr after assigning it with the address of the int variable a: %p\n", ptr);   //     the address of the variable a
	printf ("value stored at the memory location which is stored in the pointer variable ptr: %d\n", *ptr);  //    value of the integer at the location of the variable a 
	printf ("memory address of the pointer variable ptr : %p\n", &ptr);  //   the address of the variable ptr; remains the 
	
	printf ("size of pointer variable %d\n", sizeof (ptr));
	printf ("size of int variable %d\n", sizeof (a));
}
