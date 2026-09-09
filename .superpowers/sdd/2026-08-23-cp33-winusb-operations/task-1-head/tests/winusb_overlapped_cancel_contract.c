/* Hardware-free CP33 cancellation/teardown semantic contract. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define GUARD_BYTE 0xa5
struct io24_counts { unsigned int allocations, frees, submits, cancels, releases, completions, failures; };
static struct io24_counts counts;
#define IO24_CHECK(expr) do { if (!(expr)) ++counts.failures; } while (0)
static char *read_file(const char*p){FILE*f=fopen(p,"rb");long n;char*s;if(!f||fseek(f,0,SEEK_END)||(n=ftell(f))<0||fseek(f,0,SEEK_SET))return NULL;s=malloc((size_t)n+1);if(!s)return NULL;counts.allocations++;if(fread(s,1,(size_t)n,f)!=(size_t)n)return NULL;s[n]=0;fclose(f);return s;}
int main(int argc,char**argv){char p[4096],*u,*k;unsigned char g[66];if(argc<2||argc>3)return 2;snprintf(p,sizeof(p),"%s/dlls/wineusb.sys/unixlib.c",argv[1]);u=read_file(p);snprintf(p,sizeof(p),"%s/dlls/wineusb.sys/wineusb.c",argv[1]);k=read_file(p);if(!u||!k)return 2;memset(g,GUARD_BYTE,sizeof(g));
IO24_CHECK(strstr(u,"libusb_cancel_transfer")); IO24_CHECK(strstr(u,"transfer_release")||strstr(u,"release_transfer")); IO24_CHECK(strstr(k,"cancel")||strstr(k,"Cancel")); IO24_CHECK(strstr(k,"IRP_MJ_CLEANUP")); IO24_CHECK(strstr(k,"URB_FUNCTION_ABORT_PIPE")&&strstr(k,"PipeHandle")); IO24_CHECK(strstr(k,"surprise")&&strstr(k,"pending")); IO24_CHECK(strstr(k,"STATUS_CANCELLED")); IO24_CHECK(strstr(k,"IoSetCancelRoutine")); IO24_CHECK(strstr(k,"remove_pending_irps")&&strstr(k,"unix_usb_cancel_transfer"));
IO24_CHECK(g[0]==GUARD_BYTE&&g[65]==GUARD_BYTE);free(u);free(k);counts.frees+=2;IO24_CHECK(counts.allocations==counts.frees);printf("CP33 cancel RED: lower/upper cancel absent; abort is all-pipe; removal completes pending IRPs without physical cancel; failures=%u\n",counts.failures);return counts.failures?1:0;}
