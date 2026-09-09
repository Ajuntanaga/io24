/* Complete hardware-free libusb boundary for CP33 contracts. */
#include <stdlib.h>
#include <string.h>
#include <libusb.h>
struct io24_fake_counts { unsigned claim, release, detach, auto_detach, set_configuration, set_alternate, control, bulk, interrupt, cancel, clear_halt, transfer_free, close; };
static struct io24_fake_counts counts;
static const unsigned char mi05[] = {9,2,41,0,1,1,0,0x80,0xfa,9,4,5,0,0,0xff,0,0,6,9,4,5,1,2,0xff,0,0,6,7,5,0x81,2,0,2,0,7,5,0x01,2,0,2,0};
const struct io24_fake_counts *io24_fake_libusb_counts(void) { return &counts; }
const unsigned char *io24_fake_mi05(size_t *size) { *size=sizeof(mi05); return mi05; }
int libusb_init(libusb_context **ctx){ if(ctx)*ctx=(void*)1; return 0; }
void libusb_exit(libusb_context *ctx){ (void)ctx; }
int libusb_hotplug_register_callback(libusb_context *ctx, int e, int f, int v, int p, int c, libusb_hotplug_callback_fn cb, void *u, libusb_hotplug_callback_handle *h){(void)ctx;(void)e;(void)f;(void)v;(void)p;(void)c;(void)cb;(void)u;if(h)*h=1;return 0;}
void libusb_hotplug_deregister_callback(libusb_context *c,libusb_hotplug_callback_handle h){(void)c;(void)h;}
int libusb_handle_events(libusb_context *c){(void)c;return 0;} void libusb_interrupt_event_handler(libusb_context *c){(void)c;}
uint8_t libusb_get_bus_number(libusb_device *d){(void)d;return 1;} uint8_t libusb_get_port_number(libusb_device *d){(void)d;return 1;}
int libusb_get_device_descriptor(libusb_device *d,struct libusb_device_descriptor *x){(void)d;memset(x,0,sizeof(*x));return 0;}
int libusb_get_device_speed(libusb_device *d){(void)d;return LIBUSB_SPEED_HIGH;}
int libusb_open(libusb_device *d,libusb_device_handle **h){(void)d;if(h)*h=(void*)1;return 0;} libusb_device *libusb_get_device(libusb_device_handle *h){(void)h;return (void*)1;}
void libusb_close(libusb_device_handle *h){(void)h;counts.close++;}
int libusb_get_active_config_descriptor(libusb_device *d,struct libusb_config_descriptor **c){(void)d;(void)c;return LIBUSB_ERROR_NOT_FOUND;}
void libusb_free_config_descriptor(struct libusb_config_descriptor *c){free(c);}
int libusb_get_active_interface_association_descriptors(libusb_device *d,struct libusb_interface_association_descriptor_array **a){(void)d;(void)a;return LIBUSB_ERROR_NOT_SUPPORTED;}
void libusb_free_interface_association_descriptors(struct libusb_interface_association_descriptor_array *a){free(a);}
int libusb_claim_interface(libusb_device_handle *h,int i){(void)h;(void)i;counts.claim++;return 0;} int libusb_release_interface(libusb_device_handle *h,int i){(void)h;(void)i;counts.release++;return 0;}
int libusb_detach_kernel_driver(libusb_device_handle *h,int i){(void)h;(void)i;counts.detach++;return 0;} int libusb_set_auto_detach_kernel_driver(libusb_device_handle *h,int e){(void)h;(void)e;counts.auto_detach++;return 0;}
int libusb_set_configuration(libusb_device_handle *h,int c){(void)h;(void)c;counts.set_configuration++;return 0;} int libusb_set_interface_alt_setting(libusb_device_handle *h,int i,int a){(void)h;(void)i;(void)a;counts.set_alternate++;return 0;}
int libusb_control_transfer(libusb_device_handle *h,uint8_t r,uint8_t q,uint16_t v,uint16_t i,unsigned char *d,uint16_t l,unsigned int t){(void)h;(void)r;(void)q;(void)v;(void)i;(void)d;(void)t;counts.control++;return l;}
int libusb_bulk_transfer(libusb_device_handle *h,unsigned char e,unsigned char *d,int l,int *x,unsigned int t){(void)h;(void)e;(void)d;(void)t;counts.bulk++;if(x)*x=l;return 0;} int libusb_interrupt_transfer(libusb_device_handle *h,unsigned char e,unsigned char *d,int l,int *x,unsigned int t){(void)h;(void)e;(void)d;(void)t;counts.interrupt++;if(x)*x=l;return 0;}
struct libusb_transfer *libusb_alloc_transfer(int iso){size_t n=sizeof(struct libusb_transfer)+(size_t)iso*sizeof(struct libusb_iso_packet_descriptor);return calloc(1,n);} void libusb_free_transfer(struct libusb_transfer *t){counts.transfer_free++;free(t);}
int libusb_submit_transfer(struct libusb_transfer *t){(void)t;return 0;} int libusb_cancel_transfer(struct libusb_transfer *t){(void)t;counts.cancel++;return 0;} int libusb_clear_halt(libusb_device_handle *h,unsigned char e){(void)h;(void)e;counts.clear_halt++;return 0;}
const char *libusb_strerror(int e){(void)e;return "io24 fake libusb";}
