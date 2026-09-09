/* Resettable, queryable, hardware-free libusb ABI boundary. */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <libusb.h>

struct io24_fake_counts { unsigned claim, release, detach, auto_detach, set_configuration, set_alternate, control, bulk, interrupt, cancel, clear_halt, transfer_free, close; };
struct io24_fake_record { int interface_number,alternate,configuration; unsigned char endpoint,type; int length; uint8_t request_type,request; uint16_t value,index; };
static struct io24_fake_counts counts;
static struct io24_fake_record record;
static struct libusb_transfer *pending;
static int submit_result,clear_halt_result,claim_result,alternate_result,control_result;
static unsigned int alloc_count;
static const unsigned char mi05[]={9,2,41,0,1,1,0,0x80,0xfa,9,4,5,0,0,0xff,0,0,6,9,4,5,1,2,0xff,0,0,6,7,5,0x81,2,0,2,0,7,5,0x01,2,0,2,0};

void io24_fake_libusb_reset(void){if(pending){libusb_free_transfer(pending);pending=NULL;}memset(&counts,0,sizeof(counts));memset(&record,0,sizeof(record));alloc_count=0;submit_result=0;clear_halt_result=0;claim_result=0;alternate_result=0;control_result=0;}
const struct io24_fake_counts *io24_fake_libusb_counts(void){return &counts;}
const struct io24_fake_record *io24_fake_libusb_record(void){return &record;}
const unsigned char *io24_fake_mi05(size_t*size){*size=sizeof(mi05);return mi05;}
void io24_fake_libusb_set_submit_result(int r){submit_result=r;} void io24_fake_libusb_set_clear_halt_result(int r){clear_halt_result=r;}
void io24_fake_libusb_set_claim_result(int r){claim_result=r;} void io24_fake_libusb_set_alternate_result(int r){alternate_result=r;} void io24_fake_libusb_set_control_result(int r){control_result=r;}
int io24_fake_libusb_has_pending(void){return pending!=NULL;} int io24_fake_libusb_pending_type(void){return pending?pending->type:-1;} int io24_fake_libusb_pending_endpoint(void){return pending?pending->endpoint:-1;} int io24_fake_libusb_pending_length(void){return pending?pending->length:-1;} int io24_fake_libusb_pending_flags(void){return pending?pending->flags:-1;}
unsigned int io24_fake_libusb_alloc_count(void){return alloc_count;} unsigned int io24_fake_libusb_free_count(void){return counts.transfer_free;} unsigned int io24_fake_libusb_buffer_free_count(void){return 0;} unsigned int io24_fake_libusb_submit_count(void){return counts.bulk+counts.interrupt+counts.control;} unsigned int io24_fake_libusb_cancel_count(void){return counts.cancel;} unsigned int io24_fake_libusb_clear_halt_count(void){return counts.clear_halt;} unsigned char io24_fake_libusb_clear_halt_endpoint(void){return record.endpoint;}
int io24_fake_libusb_get_setup(unsigned char setup[LIBUSB_CONTROL_SETUP_SIZE]){if(!pending||pending->type!=LIBUSB_TRANSFER_TYPE_CONTROL)return -1;memcpy(setup,pending->buffer,LIBUSB_CONTROL_SETUP_SIZE);return 0;}
int io24_fake_libusb_complete(enum libusb_transfer_status status,const unsigned char*data,size_t data_length,int actual_length){struct libusb_transfer*t=pending;size_t cap;if(!t)return -1;pending=NULL;cap=t->length>(int)LIBUSB_CONTROL_SETUP_SIZE?(size_t)t->length-LIBUSB_CONTROL_SETUP_SIZE:(size_t)t->length;if(data&&data_length){if(data_length>cap)data_length=cap;memcpy(t->type==LIBUSB_TRANSFER_TYPE_CONTROL?libusb_control_transfer_get_data(t):t->buffer,data,data_length);}t->status=status;t->actual_length=actual_length;t->callback(t);if(t->flags&LIBUSB_TRANSFER_FREE_TRANSFER)libusb_free_transfer(t);return 0;}
int io24_fake_libusb_discard_pending(void){struct libusb_transfer*t=pending;if(!t)return -1;pending=NULL;libusb_free_transfer(t);return 0;}

struct libusb_transfer *libusb_alloc_transfer(int iso){size_t n;struct libusb_transfer*t;if(iso<0)return NULL;n=sizeof(struct libusb_transfer)+(size_t)iso*sizeof(struct libusb_iso_packet_descriptor);t=calloc(1,n);if(t)alloc_count++;return t;}
void libusb_free_transfer(struct libusb_transfer*t){if(!t)return;if(t->flags&LIBUSB_TRANSFER_FREE_BUFFER)free(t->buffer);counts.transfer_free++;free(t);}
int libusb_submit_transfer(struct libusb_transfer*t){if(submit_result<0)return submit_result;if(pending)return LIBUSB_ERROR_BUSY;pending=t;record.endpoint=t->endpoint;record.type=t->type;record.length=t->length;if(t->type==LIBUSB_TRANSFER_TYPE_BULK)counts.bulk++;else if(t->type==LIBUSB_TRANSFER_TYPE_INTERRUPT)counts.interrupt++;else if(t->type==LIBUSB_TRANSFER_TYPE_CONTROL)counts.control++;return 0;}
int libusb_cancel_transfer(struct libusb_transfer*t){counts.cancel++;return t==pending?0:LIBUSB_ERROR_NOT_FOUND;}
int libusb_clear_halt(libusb_device_handle*h,unsigned char e){(void)h;counts.clear_halt++;record.endpoint=e;return clear_halt_result;}
int libusb_init(libusb_context**c){if(c)*c=(void*)(uintptr_t)0x1000;return 0;} void libusb_exit(libusb_context*c){(void)c;}
int libusb_hotplug_register_callback(libusb_context*c,int e,int f,int v,int p,int k,libusb_hotplug_callback_fn cb,void*u,libusb_hotplug_callback_handle*h){(void)c;(void)e;(void)f;(void)v;(void)p;(void)k;(void)cb;(void)u;if(h)*h=1;return 0;} void libusb_hotplug_deregister_callback(libusb_context*c,libusb_hotplug_callback_handle h){(void)c;(void)h;} int libusb_handle_events(libusb_context*c){(void)c;return 0;} void libusb_interrupt_event_handler(libusb_context*c){(void)c;}
uint8_t libusb_get_bus_number(libusb_device*d){(void)d;return 1;} uint8_t libusb_get_port_number(libusb_device*d){(void)d;return 1;} int libusb_get_device_speed(libusb_device*d){(void)d;return LIBUSB_SPEED_HIGH;}
int libusb_get_device_descriptor(libusb_device*d,struct libusb_device_descriptor*x){(void)d;memset(x,0,sizeof(*x));return 0;} int libusb_open(libusb_device*d,libusb_device_handle**h){(void)d;if(h)*h=(void*)(uintptr_t)0x2000;return 0;} libusb_device *libusb_get_device(libusb_device_handle*h){(void)h;return (void*)(uintptr_t)0x3000;} void libusb_close(libusb_device_handle*h){(void)h;counts.close++;}
int libusb_get_active_config_descriptor(libusb_device*d,struct libusb_config_descriptor**c){(void)d;if(c)*c=NULL;return LIBUSB_ERROR_NOT_FOUND;} void libusb_free_config_descriptor(struct libusb_config_descriptor*c){free(c);} int libusb_get_active_interface_association_descriptors(libusb_device*d,struct libusb_interface_association_descriptor_array**a){(void)d;if(a)*a=NULL;return LIBUSB_ERROR_NOT_SUPPORTED;} void libusb_free_interface_association_descriptors(struct libusb_interface_association_descriptor_array*a){free(a);}
int libusb_claim_interface(libusb_device_handle*h,int i){(void)h;counts.claim++;record.interface_number=i;return claim_result;} int libusb_release_interface(libusb_device_handle*h,int i){(void)h;counts.release++;record.interface_number=i;return 0;} int libusb_detach_kernel_driver(libusb_device_handle*h,int i){(void)h;(void)i;counts.detach++;return 0;} int libusb_set_auto_detach_kernel_driver(libusb_device_handle*h,int e){(void)h;(void)e;counts.auto_detach++;return 0;} int libusb_set_configuration(libusb_device_handle*h,int c){(void)h;counts.set_configuration++;record.configuration=c;return 0;} int libusb_set_interface_alt_setting(libusb_device_handle*h,int i,int a){(void)h;counts.set_alternate++;record.interface_number=i;record.alternate=a;return alternate_result;}
int libusb_control_transfer(libusb_device_handle*h,uint8_t rt,uint8_t r,uint16_t v,uint16_t i,unsigned char*d,uint16_t l,unsigned int t){(void)h;(void)d;(void)t;counts.control++;record.request_type=rt;record.request=r;record.value=v;record.index=i;record.length=l;return control_result<0?control_result:l;} int libusb_bulk_transfer(libusb_device_handle*h,unsigned char e,unsigned char*d,int l,int*x,unsigned int t){(void)h;(void)d;(void)t;counts.bulk++;record.endpoint=e;record.length=l;if(x)*x=l;return 0;} int libusb_interrupt_transfer(libusb_device_handle*h,unsigned char e,unsigned char*d,int l,int*x,unsigned int t){(void)h;(void)d;(void)t;counts.interrupt++;record.endpoint=e;record.length=l;if(x)*x=l;return 0;}
const char *libusb_strerror(int e){(void)e;return "io24 fake libusb";}
