/* Hardware-free CP33 generic-function-driver contract. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define GUARD_BYTE 0xa5
struct io24_counts { unsigned int allocations, frees, submits, cancels, releases, completions, failures; };
static struct io24_counts counts;
#define IO24_CHECK(expr) do { if (!(expr)) ++counts.failures; } while (0)
static const unsigned char mi05_configuration[] = {
    9,2,41,0,1,1,0,0x80,0xfa, 9,4,5,0,0,0xff,0,0,6,
    9,4,5,1,2,0xff,0,0,6, 7,5,0x81,2,0,2,0, 7,5,0x01,2,0,2,0
};
static char *read_file(const char *path)
{
    FILE *f = fopen(path, "rb"); long n; char *p;
    if (!f || fseek(f,0,SEEK_END) || (n=ftell(f))<0 || fseek(f,0,SEEK_SET)) return NULL;
    if (!(p=malloc((size_t)n+1))) return NULL;
    counts.allocations++;
    if (fread(p,1,(size_t)n,f)!=(size_t)n) return NULL;
    p[n]=0;
    fclose(f);
    return p;
}
int main(int argc, char **argv)
{
    char path[4096], *source; unsigned char guarded[43];
    if (argc != 2) return 2;
    snprintf(path,sizeof(path),"%s/dlls/winusb.sys/main.c",argv[1]);
    if (!(source=read_file(path))) { fputs("HARNESS: missing function-driver source\n",stderr); return 2; }
    memset(guarded,GUARD_BYTE,sizeof(guarded)); memcpy(guarded+1,mi05_configuration,sizeof(mi05_configuration));
    IO24_CHECK(guarded[0]==GUARD_BYTE && guarded[sizeof(guarded)-1]==GUARD_BYTE);
    IO24_CHECK(mi05_configuration[13]==0 && mi05_configuration[22]==2);
    IO24_CHECK(mi05_configuration[29]==0x81 && mi05_configuration[31]==0x00);
    IO24_CHECK(strstr(source,"driver_create") && !strstr(source,"MajorFunction[IRP_MJ_CREATE] = driver_unsupported"));
    IO24_CHECK(strstr(source,"driver_device_control") && !strstr(source,"MajorFunction[IRP_MJ_DEVICE_CONTROL] = driver_unsupported"));
    IO24_CHECK(strstr(source,"IRP_MJ_CLEANUP"));
    IO24_CHECK(strstr(source,"IOCTL") && strstr(source,"select") && strstr(source,"control"));
    free(source); counts.frees++; IO24_CHECK(counts.allocations==counts.frees);
    printf("CP33 function-driver RED: create/device-control/session/select/control absent failures=%u\n",counts.failures);
    return counts.failures ? 1 : 0;
}
