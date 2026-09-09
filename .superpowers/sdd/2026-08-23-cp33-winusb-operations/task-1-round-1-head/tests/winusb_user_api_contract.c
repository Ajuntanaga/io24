/* Executed host contract for the actual winusb.dll production module. */
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "windef.h"
#include "winbase.h"
#include "winusb.h"
#include "wine/debug.h"

#define GUARD_BYTE 0xa5
struct io24_counts { unsigned int allocations, frees, submits, cancels, releases, completions, failures; };
static struct io24_counts counts;
#define IO24_CHECK(expr) do { if (!(expr)) ++counts.failures; } while (0)

struct io24_fake_win32
{
    DWORD last_error; BOOL ioctl_result, overlapped_result; DWORD ioctl_error, bytes;
    DWORD codes[64], in_lengths[64], out_lengths[64]; void *overlapped[64];
    unsigned int code_count, duplicates, closes;
};
static struct io24_fake_win32 fake;
enum vendor_operation
{
    VENDOR_INITIALIZE, VENDOR_QUERY, VENDOR_DESCRIPTOR, VENDOR_GET_POLICY,
    VENDOR_SET_POLICY, VENDOR_SET_ALT, VENDOR_CONTROL, VENDOR_READ,
    VENDOR_WRITE, VENDOR_OVERLAPPED, VENDOR_ABORT, VENDOR_RESET,
    VENDOR_ASSOCIATED, VENDOR_FREE
};
struct vendor_call { enum vendor_operation operation; uintptr_t argument[5]; BOOL result; };
static struct vendor_call vendor_calls[32];
static unsigned int vendor_call_count;
int __cdecl __wine_dbg_header(enum __wine_debug_class c,struct __wine_debug_channel*d,const char*f){(void)c;(void)d;(void)f;return -1;}
int __cdecl __wine_dbg_output(const char*s){(void)s;return 0;}
const char *__cdecl __wine_dbg_strdup(const char*s){return s;}
static void fake_reset(void) { memset(&fake,0,sizeof(fake)); memset(&counts,0,sizeof(counts)); fake.ioctl_result=TRUE; fake.overlapped_result=TRUE; fake.bytes=4; }

LPVOID WINAPI HeapAlloc(HANDLE h,DWORD f,SIZE_T n){void*p;(void)h;(void)f;p=calloc(1,n?n:1);if(p)counts.allocations++;return p;}
BOOL WINAPI HeapFree(HANDLE h,DWORD f,LPVOID p){(void)h;(void)f;if(p){free(p);counts.frees++;}return TRUE;}
BOOL WINAPI CloseHandle(HANDLE h){(void)h;fake.closes++;counts.releases++;return TRUE;}
BOOL WINAPI DuplicateHandle(HANDLE a,HANDLE source,HANDLE b,HANDLE *target,DWORD c,BOOL d,DWORD e)
{(void)a;(void)b;(void)c;(void)d;(void)e;fake.duplicates++;if(target)*target=(HANDLE)((uintptr_t)source+0x100);return TRUE;}
BOOL WINAPI DeviceIoControl(HANDLE d,DWORD code,void*in,DWORD il,void*out,DWORD ol,DWORD*bytes,OVERLAPPED*ov)
{unsigned int s=fake.code_count++;(void)d;(void)in;if(s<64){fake.codes[s]=code;fake.in_lengths[s]=il;fake.out_lengths[s]=ol;fake.overlapped[s]=ov;}counts.submits++;if(out&&ol)memset(out,0x3c,ol);if(bytes)*bytes=fake.bytes;if(!fake.ioctl_result)fake.last_error=fake.ioctl_error;return fake.ioctl_result;}
BOOL WINAPI GetOverlappedResult(HANDLE h,OVERLAPPED*ov,DWORD*b,BOOL w){(void)h;(void)ov;(void)w;counts.completions++;if(b)*b=fake.bytes;return fake.overlapped_result;}

typedef BOOL (WINAPI *fn_abort)(WINUSB_INTERFACE_HANDLE,UCHAR);
typedef BOOL (WINAPI *fn_control)(WINUSB_INTERFACE_HANDLE,void*,UCHAR*,ULONG,ULONG*,OVERLAPPED*);
typedef BOOL (WINAPI *fn_free)(WINUSB_INTERFACE_HANDLE);
typedef BOOL (WINAPI *fn_associated)(WINUSB_INTERFACE_HANDLE,UCHAR,PWINUSB_INTERFACE_HANDLE);
typedef BOOL (WINAPI *fn_descriptor)(WINUSB_INTERFACE_HANDLE,UCHAR,UCHAR,USHORT,UCHAR*,ULONG,ULONG*);
typedef BOOL (WINAPI *fn_overlapped)(WINUSB_INTERFACE_HANDLE,OVERLAPPED*,ULONG*,BOOL);
typedef BOOL (WINAPI *fn_get_policy)(WINUSB_INTERFACE_HANDLE,UCHAR,ULONG,ULONG*,void*);
typedef BOOL (WINAPI *fn_initialize)(HANDLE,PWINUSB_INTERFACE_HANDLE);
typedef BOOL (WINAPI *fn_query)(WINUSB_INTERFACE_HANDLE,ULONG,ULONG*,void*);
typedef BOOL (WINAPI *fn_pipe_io)(WINUSB_INTERFACE_HANDLE,UCHAR,UCHAR*,ULONG,ULONG*,OVERLAPPED*);
typedef BOOL (WINAPI *fn_reset)(WINUSB_INTERFACE_HANDLE,UCHAR);
typedef BOOL (WINAPI *fn_alt)(WINUSB_INTERFACE_HANDLE,UCHAR);
typedef BOOL (WINAPI *fn_set_policy)(WINUSB_INTERFACE_HANDLE,UCHAR,ULONG,ULONG,void*);
struct functions { fn_abort abort_pipe; fn_control control; fn_free free_handle; fn_associated associated; fn_descriptor descriptor; fn_overlapped overlapped; fn_get_policy get_policy; fn_initialize initialize; fn_query query; fn_pipe_io read_pipe; fn_reset reset_pipe; fn_alt set_alt; fn_set_policy set_policy; fn_pipe_io write_pipe; };

static void *feature_symbol(void*m,const char*n){(void)n;return dlsym(m,n);}
#define LOAD(field,name) *(void **)&f->field=feature_symbol(module,name)
static void load_functions(void*module,struct functions*f)
{memset(f,0,sizeof(*f));LOAD(abort_pipe,"WinUsb_AbortPipe");LOAD(control,"WinUsb_ControlTransfer");LOAD(free_handle,"WinUsb_Free");LOAD(associated,"WinUsb_GetAssociatedInterface");LOAD(descriptor,"WinUsb_GetDescriptor");LOAD(overlapped,"WinUsb_GetOverlappedResult");LOAD(get_policy,"WinUsb_GetPipePolicy");LOAD(initialize,"WinUsb_Initialize");LOAD(query,"WinUsb_QueryDeviceInformation");LOAD(read_pipe,"WinUsb_ReadPipe");LOAD(reset_pipe,"WinUsb_ResetPipe");LOAD(set_alt,"WinUsb_SetCurrentAlternateSetting");LOAD(set_policy,"WinUsb_SetPipePolicy");LOAD(write_pipe,"WinUsb_WritePipe");}

static void test_initialize(const struct functions*f){WINUSB_INTERFACE_HANDLE h=NULL;unsigned int before=counts.failures;fake_reset();counts.failures=before;if(f->initialize)IO24_CHECK(f->initialize((HANDLE)(uintptr_t)0x1110,&h)&&h);IO24_CHECK(counts.submits>=1);}
static void test_handles(const struct functions*f){WINUSB_INTERFACE_HANDLE a=NULL;unsigned int before=counts.failures;fake_reset();counts.failures=before;if(f->associated)IO24_CHECK(f->associated((void*)0x2200,0,&a)&&a);if(f->free_handle){IO24_CHECK(f->free_handle(a));IO24_CHECK(f->free_handle((void*)0x2200));}IO24_CHECK(counts.releases>=1);}
static void test_descriptors(const struct functions*f){unsigned char g[34];ULONG n=0,s=0,sl=sizeof(s);unsigned int before=counts.failures;fake_reset();counts.failures=before;memset(g,GUARD_BYTE,sizeof(g));if(f->descriptor)IO24_CHECK(f->descriptor((void*)0x2200,1,0,0,g+1,32,&n));if(f->query)IO24_CHECK(f->query((void*)0x2200,1,&sl,&s));IO24_CHECK(g[0]==GUARD_BYTE&&g[33]==GUARD_BYTE);IO24_CHECK(counts.submits==2);}
static void test_policy(const struct functions*f){static const struct{UCHAR pipe,policy;ULONG length,value;}q[]={{0,3,0,0},{0,9,0,0},{1,1,0,0},{0x81,2,0,0},{0x81,4,0,0},{0x81,5,0,0},{0x81,6,0,0},{0x81,7,1,1},{0x81,8,4,0x10000}};unsigned int i,before=counts.failures;ULONG n=4,v=0;fake_reset();counts.failures=before;for(i=0;i<9;i++){if(q[i].policy==8){if(f->get_policy)IO24_CHECK(f->get_policy((void*)0x2200,q[i].pipe,q[i].policy,&n,&v));}else if(f->set_policy)IO24_CHECK(f->set_policy((void*)0x2200,q[i].pipe,q[i].policy,q[i].length,(void*)&q[i].value));}if(f->set_alt)IO24_CHECK(f->set_alt((void*)0x2200,1));IO24_CHECK(counts.submits==10);}
static void test_transfer(const struct functions*f){unsigned char g[34];ULONG n=0;OVERLAPPED ov={0};struct{UCHAR type,request;USHORT value,index,length;}setup={0x41,1,2,5,32};unsigned int before=counts.failures;fake_reset();counts.failures=before;memset(g,GUARD_BYTE,sizeof(g));if(f->control)IO24_CHECK(f->control((void*)0x2200,&setup,g+1,32,&n,NULL));if(f->read_pipe)IO24_CHECK(f->read_pipe((void*)0x2200,0x81,g+1,32,&n,&ov));if(f->write_pipe)IO24_CHECK(f->write_pipe((void*)0x2200,1,g+1,32,&n,NULL));if(f->overlapped)IO24_CHECK(f->overlapped((void*)0x2200,&ov,&n,TRUE));IO24_CHECK(g[0]==GUARD_BYTE&&g[33]==GUARD_BYTE);IO24_CHECK(counts.submits==3&&counts.completions==1);}
static void test_cancel(const struct functions*f){unsigned int before=counts.failures;fake_reset();counts.failures=before;if(f->abort_pipe)IO24_CHECK(f->abort_pipe((void*)0x2200,0x81));if(f->reset_pipe)IO24_CHECK(f->reset_pipe((void*)0x2200,0x81));IO24_CHECK(counts.submits==2);}
static void test_vendor_sequence(const struct functions*f)
{
    WINUSB_INTERFACE_HANDLE root=NULL,associated=NULL;unsigned char g[34];ULONG n=0,v=0,vl=sizeof(v);OVERLAPPED ov={0};BOOL ok;
    struct{UCHAR type,request;USHORT value,index,length;}setup={0x41,1,2,5,32};
    static const struct{UCHAR pipe,policy;ULONG length,value;}q[]={{0,3,0,0},{0,9,0,0},{1,1,0,0},{0x81,2,0,0},{0x81,4,0,0},{0x81,5,0,0},{0x81,6,0,0},{0x81,7,1,1}};
    static const enum vendor_operation expected[] =
    {
        VENDOR_INITIALIZE,VENDOR_QUERY,VENDOR_DESCRIPTOR,VENDOR_DESCRIPTOR,VENDOR_GET_POLICY,
        VENDOR_SET_POLICY,VENDOR_SET_POLICY,VENDOR_SET_POLICY,VENDOR_SET_POLICY,
        VENDOR_SET_POLICY,VENDOR_SET_POLICY,VENDOR_SET_POLICY,VENDOR_SET_POLICY,VENDOR_SET_ALT,
        VENDOR_CONTROL,VENDOR_CONTROL,VENDOR_READ,VENDOR_READ,VENDOR_WRITE,VENDOR_WRITE,
        VENDOR_OVERLAPPED,VENDOR_ABORT,VENDOR_RESET,VENDOR_ASSOCIATED,VENDOR_FREE,VENDOR_FREE
    };
    unsigned int i,before=counts.failures;
#define VENDOR_RECORD(op_value,result_value,a0,a1,a2,a3,a4) do { \
    struct vendor_call *call=&vendor_calls[vendor_call_count++]; \
    call->operation=(op_value);call->result=(result_value);call->argument[0]=(uintptr_t)(a0); \
    call->argument[1]=(uintptr_t)(a1);call->argument[2]=(uintptr_t)(a2); \
    call->argument[3]=(uintptr_t)(a3);call->argument[4]=(uintptr_t)(a4); \
} while (0)
    fake_reset();counts.failures=before;vendor_call_count=0;memset(vendor_calls,0,sizeof(vendor_calls));memset(g,GUARD_BYTE,sizeof(g));
    ok=f->initialize&&f->initialize((HANDLE)(uintptr_t)0x1110,&root);VENDOR_RECORD(VENDOR_INITIALIZE,ok,0x1110,0,0,0,0);IO24_CHECK(ok&&root);
    ok=f->query&&f->query(root,1,&vl,&v);VENDOR_RECORD(VENDOR_QUERY,ok,root,1,sizeof(v),v,0);IO24_CHECK(ok);
    ok=f->descriptor&&f->descriptor(root,1,0,0,g+1,32,&n);VENDOR_RECORD(VENDOR_DESCRIPTOR,ok,root,1,0,0,32);IO24_CHECK(ok);
    ok=f->descriptor&&f->descriptor(root,3,1,0x409,g+1,32,&n);VENDOR_RECORD(VENDOR_DESCRIPTOR,ok,root,3,1,0x409,32);IO24_CHECK(ok);
    vl=sizeof(v);ok=f->get_policy&&f->get_policy(root,0x81,8,&vl,&v);VENDOR_RECORD(VENDOR_GET_POLICY,ok,root,0x81,8,vl,v);IO24_CHECK(ok);
    for(i=0;i<sizeof(q)/sizeof(q[0]);i++){ok=f->set_policy&&f->set_policy(root,q[i].pipe,q[i].policy,q[i].length,(void*)&q[i].value);VENDOR_RECORD(VENDOR_SET_POLICY,ok,root,q[i].pipe,q[i].policy,q[i].length,q[i].value);IO24_CHECK(ok);}
    ok=f->set_alt&&f->set_alt(root,1);VENDOR_RECORD(VENDOR_SET_ALT,ok,root,1,0,0,0);IO24_CHECK(ok);
    ok=f->control&&f->control(root,&setup,g+1,32,&n,NULL);VENDOR_RECORD(VENDOR_CONTROL,ok,root,0x41010002,5,32,0);IO24_CHECK(ok);
    ok=f->control&&f->control(root,&setup,g+1,32,&n,&ov);VENDOR_RECORD(VENDOR_CONTROL,ok,root,0x41010002,5,32,&ov);IO24_CHECK(ok);
    ok=f->read_pipe&&f->read_pipe(root,0x81,g+1,32,&n,NULL);VENDOR_RECORD(VENDOR_READ,ok,root,0x81,32,0,0);IO24_CHECK(ok);
    ok=f->read_pipe&&f->read_pipe(root,0x81,g+1,32,&n,&ov);VENDOR_RECORD(VENDOR_READ,ok,root,0x81,32,&ov,0);IO24_CHECK(ok);
    ok=f->write_pipe&&f->write_pipe(root,1,g+1,32,&n,NULL);VENDOR_RECORD(VENDOR_WRITE,ok,root,1,32,0,0);IO24_CHECK(ok);
    ok=f->write_pipe&&f->write_pipe(root,1,g+1,32,&n,&ov);VENDOR_RECORD(VENDOR_WRITE,ok,root,1,32,&ov,0);IO24_CHECK(ok);
    ok=f->overlapped&&f->overlapped(root,&ov,&n,TRUE);VENDOR_RECORD(VENDOR_OVERLAPPED,ok,root,&ov,TRUE,n,0);IO24_CHECK(ok);
    ok=f->abort_pipe&&f->abort_pipe(root,0x81);VENDOR_RECORD(VENDOR_ABORT,ok,root,0x81,0,0,0);IO24_CHECK(ok);
    ok=f->reset_pipe&&f->reset_pipe(root,0x81);VENDOR_RECORD(VENDOR_RESET,ok,root,0x81,0,0,0);IO24_CHECK(ok);
    ok=f->associated&&f->associated(root,0,&associated);VENDOR_RECORD(VENDOR_ASSOCIATED,ok,root,0,associated,0,0);IO24_CHECK(ok&&associated&&associated!=root);
    ok=f->free_handle&&f->free_handle(associated);VENDOR_RECORD(VENDOR_FREE,ok,associated,0,0,0,0);IO24_CHECK(ok);
    ok=f->free_handle&&f->free_handle(root);VENDOR_RECORD(VENDOR_FREE,ok,root,0,0,0,0);IO24_CHECK(ok);
    IO24_CHECK(vendor_call_count==sizeof(expected)/sizeof(expected[0]));
    for(i=0;i<vendor_call_count&&i<sizeof(expected)/sizeof(expected[0]);i++)IO24_CHECK(vendor_calls[i].operation==expected[i]&&vendor_calls[i].result);
    for(i=0;i<sizeof(q)/sizeof(q[0]);i++)IO24_CHECK(vendor_calls[5+i].argument[1]==q[i].pipe&&vendor_calls[5+i].argument[2]==q[i].policy&&vendor_calls[5+i].argument[3]==q[i].length&&vendor_calls[5+i].argument[4]==q[i].value);
    IO24_CHECK(vendor_calls[2].argument[1]==1&&vendor_calls[2].argument[2]==0&&vendor_calls[2].argument[3]==0&&vendor_calls[2].argument[4]==32);
    IO24_CHECK(vendor_calls[3].argument[1]==3&&vendor_calls[3].argument[2]==1&&vendor_calls[3].argument[3]==0x409&&vendor_calls[3].argument[4]==32);
    IO24_CHECK(vendor_calls[14].argument[1]==0x41010002&&vendor_calls[14].argument[2]==5&&vendor_calls[14].argument[3]==32&&vendor_calls[14].argument[4]==0);
    IO24_CHECK(vendor_calls[15].argument[4]==(uintptr_t)&ov&&vendor_calls[17].argument[3]==(uintptr_t)&ov&&vendor_calls[19].argument[3]==(uintptr_t)&ov);
    IO24_CHECK(vendor_calls[24].argument[0]==(uintptr_t)associated&&vendor_calls[25].argument[0]==(uintptr_t)root);
    IO24_CHECK(g[0]==GUARD_BYTE&&g[33]==GUARD_BYTE);IO24_CHECK(counts.submits>=19);IO24_CHECK(counts.completions==1);IO24_CHECK(counts.releases>=1);
#undef VENDOR_RECORD
}
static void run_group(const char*m,const struct functions*f){if(!strcmp(m,"--vendor")){test_vendor_sequence(f);return;}if(!strcmp(m,"--red")||!strcmp(m,"--initialize"))test_initialize(f);if(!strcmp(m,"--red")||!strcmp(m,"--handles"))test_handles(f);if(!strcmp(m,"--red")||!strcmp(m,"--descriptors"))test_descriptors(f);if(!strcmp(m,"--red")||!strcmp(m,"--policy"))test_policy(f);if(!strcmp(m,"--red")||!strcmp(m,"--transfer"))test_transfer(f);if(!strcmp(m,"--red")||!strcmp(m,"--cancel"))test_cancel(f);if(!strcmp(m,"--red"))test_vendor_sequence(f);}
int main(int argc,char**argv){void*m;struct functions f;if(argc!=3)return 2;m=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);if(!m){fprintf(stderr,"HARNESS: dlopen production module: %s\n",dlerror());return 2;}fake_reset();load_functions(m,&f);run_group(argv[2],&f);dlclose(m);printf("CP33 public executed mode=%s submits=%u releases=%u completions=%u failures=%u\n",argv[2],counts.submits,counts.releases,counts.completions,counts.failures);return counts.failures?1:0;}
