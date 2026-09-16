#include<stdio.h>

void swap1 (int a, int b)
{
	int tmp;
	printf ("\nSTART function swap1\n");
	printf ("BEFORE: value of a: %d, value of b: %d\n", a, b);
	tmp = a;
	a = b;
	b = tmp;
	printf ("AFTER: value of a: %d, value of b: %d\n", a, b);
	printf ("\nEND function swap1\n");
}

void swap2 (int *a, int *b)
{
	int tmp;
	printf ("\nSTART function swap2\n");
	printf ("BEFORE: address of a: %p, address of b: %p\n", a, b);
	printf ("BEFORE: value of a: %d, value of b: %d\n", *a, *b);
	tmp = *a;
	*a = *b;
	*b = tmp;
	printf ("AFTER: value of a: %d, value of b: %d\n", *a, *b);
	printf ("AFTER: address of a: %p, address of b: %p\n", a, b);
	printf ("\nEND function swap2\n");
}



int main ()
{
	int a = 10, b =20;

	
	printf ("in main, value of a: %d, value of b: %d\n", a, b);
	swap1 (a,b);
	printf ("in main, value of a: %d, value of b: %d\n\n\n", a, b);

	printf ("in main, address of a: %p, address of b: %p\n", &a, &b);
	printf ("in main, value of a: %d, value of b: %d\n", a, b);
	swap2(&a, &b);
	printf ("in main, value of a: %d, value of b: %d\n", a, b);
	printf ("in main, address of a: %p, address of b: %p\n", &a, &b);
}
