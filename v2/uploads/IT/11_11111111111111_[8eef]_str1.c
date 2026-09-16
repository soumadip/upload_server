#include<stdio.h>
#include<string.h>

int main ()
{
	char str1[] = "abc";
	char str2[] ="def";

	printf("%s\n", str1);
	printf("%s\n", str2);
	printf("%s\n", strcat(str2, str1));
	printf("%s\n", str1);
	printf("%s\n", str2);
	return 0;
}
