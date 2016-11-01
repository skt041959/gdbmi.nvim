#include <stdio.h>

long seqsum(long n) {
    long ret = 0;
    int i;
    for(i=0; i<n; i++)
    {
        ret = 0;
        int j = 0;
        for(j=0; j<n; j++)
        {
            ret += 1;
        }
    }
    return ret;
}

int main () {
    long a, b;

    printf("Hello world\n");

    printf("Enter a number:\n");
    // scanf("%ld", &a);
    a = 1000000;

    b = seqsum(a);

    printf("%ld\n", b);

    return 0;
}
