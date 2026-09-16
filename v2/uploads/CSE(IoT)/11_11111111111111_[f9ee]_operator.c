#include<stdio.h>

int main ()
{
	int a =10;
	int b = 20;
	int c = 30;
	int d;
	float f;

	d = b/c;
	f = (float)c/b;

	printf ("%d, %d %f \n", d, (int)f, f);
}
