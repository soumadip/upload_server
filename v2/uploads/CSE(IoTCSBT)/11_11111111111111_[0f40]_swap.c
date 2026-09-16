#include<stdio.h>


void swap(int *a, int *b)
{
	int tmp;
	printf ("F: a = %d b = %d \n", *a, *b);
	tmp = *a;
	*a = *b;
	*b = tmp;
	printf ("F: a = %d b = %d \n", *a, *b);
}

int main ()
{
	int a = 20, b = 30;

	printf ("a = %d b = %d \n", a, b);
	swap (&a, &b);

	printf ("a = %d b = %d \n", a, b);
	return 0;
}
