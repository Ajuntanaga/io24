/* Hardware-free CP33 lower URB semantic contract. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define GUARD_BYTE 0xa5
struct io24_counts { unsigned int allocations, frees, submits, cancels, releases, completions, failures; };
static struct io24_counts counts;
#define IO24_CHECK(expr) do { if (!(expr)) ++counts.failures; } while (0)
static char *read_file(const char *p){FILE*f=fopen(p,"rb");long n;char*s;if(!f||fseek(f,0,SEEK_END)||(n=ftell(f))<0||fseek(f,0,SEEK_SET))return NULL;s=malloc((size_t)n+1);if(!s)return NULL;counts.allocations++;if(fread(s,1,(size_t)n,f)!=(size_t)n)return NULL;s[n]=0;fclose(f);return s;}
int main(int argc,char**argv){char p[4096],*s;unsigned char g[43];if(argc<2||argc>3)return 2;snprintf(p,sizeof(p),"%s/dlls/wineusb.sys/unixlib.c",argv[1]);if(!(s=read_file(p)))return 2;memset(g,GUARD_BYTE,sizeof(g));
IO24_CHECK(strstr(s,"libusb_claim_interface")); IO24_CHECK(strstr(s,"libusb_release_interface")); IO24_CHECK(!strstr(s,"libusb_detach_kernel_driver")); IO24_CHECK(!strstr(s,"libusb_set_auto_detach_kernel_driver")); IO24_CHECK(!strstr(s,"libusb_set_configuration"));
IO24_CHECK(strstr(s,"libusb_set_interface_alt_setting")); IO24_CHECK(strstr(s,"libusb_control_transfer")); IO24_CHECK(strstr(s,"libusb_cancel_transfer")); IO24_CHECK(strstr(s,"pipe")&&strstr(s,"generation")); IO24_CHECK(strstr(s,"libusb_bulk_transfer")||strstr(s,"libusb_fill_bulk_transfer"));
IO24_CHECK(strstr(s,"libusb_clear_halt") && strstr(s,"STATUS_UNSUCCESSFUL"));
IO24_CHECK(g[0]==GUARD_BYTE&&g[42]==GUARD_BYTE);free(s);counts.frees++;IO24_CHECK(counts.allocations==counts.frees);printf("CP33 lower RED: select-interface/control/cancel/function-claims missing; reset backend error is unconditionally reported success; failures=%u\n",counts.failures);return counts.failures?1:0;}
