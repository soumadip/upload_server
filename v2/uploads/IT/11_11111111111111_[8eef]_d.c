#include<stdio.h>

void fun(int x, int y)
{
printf("evaluating fun(%d,%d) \n",x, y);
	if (x>y)
	{	
		printf("calling fun(%d,%d) \n",y+1, x-1);
		fun(y+1, x-1);
	}
	else if (x<y)
	{   
		printf("calling fun(%d,%d) \n",y-1, x+1);
		fun(y-1, x+1);
	}
	
	printf("%d %d\n", x, y);
}


typedef struct
{
	float real;
	float imaginary;
}Q;
void print (Q n)
{
	printf ("%f %f\n", n.real, n.imaginary);
	if (n.real != 0)
		printf ("%f", n.real);

	if (n.imaginary != 0)
	{
		printf (" %c ", (n.imaginary < 0) ? '-' : '+');
		if (n.imaginary != 1 && n.imaginary != -1)
			printf ("%f", (n.imaginary < 0) ? -n.imaginary : n.imaginary);
		printf ("i");
	}
}

void multiply(Q c1, Q c2)
{
	Q result;
	result.real = (c1.real * c2.real) - (c1.imaginary * c2.imaginary);
	result.imaginary = (c1.real * c2.imaginary) + (c1.imaginary * c2.real);
	print (result);
}

void sat_sun (int m)
{
     int days = 0, d, i;
     int sat = 7, sun =1;
      
      i = m-1;
      for (i=1; i<=m; i++)
      {
	d = days;
	      if (i==1 || i==3 || i==5 || i==7 || i==8 || i==10 || i==12)
		      days +=  31;
	      else if (i==2)
		      days += 28;
	      else
		      days += 30;	
      }

      while (sat<d) sat += 7;
      while (sun<d) sun += 7;

      while (sun<= days)
	{
		printf ("%d ", sun-d);
		sun+=7;
	}
      while (sat<= days)
	{
		printf ("%d ", sat-d);
		sat+=7;
	}
}
int main ()
{
	//fun (10,2);

	Q x, y;
	x.real = 1, x.imaginary = 2;
	y.real = -2, y.imaginary = -1;
	//multiply(x,y);

	sat_sun (9);

}

/*
	int n = 100;

	int count = 0, x, y, i;
	for (i=1; i<=n; i++)
	{
		for(x=i; x%5==0; x/=5)
			count++;
	}
	printf ("%d\n", count);
	char str[100]; //assuming input string is less than size 100
	i=0;
	scanf ("%s", str);
	while (str[i]!='\0')
	{
		if (str[i] <='z' && str[i] >= 'a')
			str[i] = str[i] - ('a' - 'A');
		i++;
	}
	printf ("%s", str);

int result=0;
scanf("%d %d", &x, &y); //x is the divident and y is the divisor

while ((x - y)>0)
{
	x = x - y;
	result++;
}
printf ("%d/%d = %d", x, y, result);
}*/
