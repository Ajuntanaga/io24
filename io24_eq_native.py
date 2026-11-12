"""Native Passive/Vintage analog-network EQ coefficient calculations.

Recovered with REA from UC 4.7.2 designer routines. No binary is read or
executed. Arithmetic order and binary32 rounding are intentional: changing
association can change the coefficients sent to the device. The intermediate
polynomial terms follow the recovered circuit equations; the golden fixtures
record the independent instruction interpreter's output.
"""
import struct

class _F(float):
    """One scalar SSE-style binary32 operation at a time."""
    def __new__(cls, value):
        return float.__new__(cls, struct.unpack('<f', struct.pack('<f', value))[0])
    def __add__(self, other): return _F(float(self) + float(_F(other)))
    def __sub__(self, other): return _F(float(self) - float(_F(other)))
    def __mul__(self, other): return _F(float(self) * float(_F(other)))
    def __truediv__(self, other): return _F(float(self) / float(_F(other)))
    def __radd__(self, other): return _F(other) + self
    def __rsub__(self, other): return _F(other) - self
    def __rmul__(self, other): return _F(other) * self
    def __rtruediv__(self, other): return _F(other) / self
    def __neg__(self): return _F(-float(self))


def _normalize(denominator, numerator, gain):
    scale = _F(1) / denominator[0]
    output = [scale * numerator[0] * gain]
    for a, b in zip(denominator[1:], numerator[1:]):
        output.extend((-(scale * a), scale * b * gain))
    return tuple(float(v) for v in output)


def _bilinear3(a, period):
    squared = period * period
    cubed = squared * period
    second = a[2] * 4.0 * period
    third24 = a[3] * 24.0
    third8 = a[3] * 8.0
    first = (a[1] + a[1]) * squared
    constant = a[0] * cubed
    constant3 = a[0] * 3.0 * cubed
    return ((third8 + second) + (constant + first),
            ((constant3 + first) - second) - third24,
            ((constant3 - first) - second) + third24,
            ((constant - first) + second) - third8)


def passive_low(index, boost, attenuation, rate):
    param_3, param_4 = (_F(boost), _F(attenuation))
    param_5 = _F(1) / _F(rate)
    t6 = param_4 * _F(9980.0) + _F(100.00001)
    t11 = param_3 * _F(980.0) + _F(100.0)
    t2, t4 = map(_F, ((_F(2.2e-06), _F(1e-07)), (_F(1e-06), _F(4.7e-08)), (_F(4.7e-07), _F(2.2e-08)), (_F(3.3e-07), _F(1.5e-08)))[index])
    t9 = t2 * t11 * t6
    t8 = t9 * (t4 * _F(10010000000000.0))
    t1 = t8 * _F(4.0)
    t9 = t9 * (t4 * _F(131120000000000.0))
    t5 = ((t4 * _F(12011000000.0) + t2 * _F(10000000.0)) * t11 + t4 * _F(10010000000000.0)) * t6
    t7 = (t11 * _F(1011000.0) + _F(10000000.0)) * t6 + _F(10010000000000.0) + t11 * _F(12011000000.0)
    t3 = param_5 * param_5
    t10 = (t11 * _F(1011000.0) + _F(11120001000.0)) * t6 + _F(131120000000000.0) + t11 * _F(12011000000.0)
    t6 = (((t2 * _F(11120001000.0) + t4 * _F(1000000000.0)) + (t4 * _F(10011000000.0) + t4 * _F(1000000000.0))) * t11 + t4 * _F(131120000000000.0)) * t6
    t4 = (t11 * (t2 * _F(10000000.0)) * _F(2002000.0) + t5 + t5) * param_5
    local_c4 = (t7 + t7) * t3 - t8 * _F(8.0)
    param_5 = (t2 * t11 * _F(262240000000000.0) + t6 + t6) * param_5
    local_c8 = t4 + t1 + t7 * t3
    local_c0 = t1 - t4 + t7 * t3
    t6 = t9 * _F(4.0)
    local_b8 = param_5 + t6 + t10 * t3
    local_b0 = t6 - param_5 + t10 * t3
    local_b4 = (t10 + t10) * t3 - t9 * _F(8.0)
    return _normalize((local_b8, local_b4, local_b0), (local_c8, local_c4, local_c0), _F(struct.unpack('<f', bytes.fromhex('9a995041'))[0]))

def passive_high(index, boost, attenuation, attenuation_index, bandwidth, rate):
    param_3, param_4, param_6 = (_F(boost), _F(attenuation), _F(bandwidth))
    param_7 = _F(1) / _F(rate)
    t7 = _F(9990.0) - param_3 * _F(998.0)
    t21 = param_6 * _F(99.799995) + _F(1.0)
    t8 = _F(999.0) - param_6 * _F(99.799995)
    t16 = param_3 * _F(998.0) + _F(10.0)
    t10 = param_4 * _F(206.79999) + _F(110.0)
    t4, local_res8 = map(_F, ((_F(1.5e-08), _F(0.175)), (_F(1.5e-08), _F(0.1)), (_F(1e-08), _F(0.09)), (_F(1e-08), _F(0.065)), (_F(6.8e-09), _F(0.035)), (_F(6.8e-09), _F(0.023)), (_F(3.3e-09), _F(0.0266)))[index])
    t1 = _F((_F(1.97e-07), _F(9.4e-08), _F(4.7e-08))[attenuation_index])
    t12 = t16 + t8
    t13 = t8 + _F(75.0)
    t5 = t12 + _F(75.0)
    t20 = t13 * t21 + t8 * _F(75.0)
    t2 = t16 + t10
    t15 = t2 * t8 + t12
    t11 = ((t8 + _F(10000.0)) * t7 + (t12 + t7)) + (t12 * _F(10000.0) + t16 * t8)
    t3 = (t16 + t7 + _F(10001.0)) * t21 + t11
    t9 = t10 + _F(10000.0)
    t6 = t2 * t7
    t17 = (((t13 * t16 + (t13 + _F(10000.0)) * t7) + ((t5 * _F(10000.0) + _F(75.0)) + (t12 + t7))) * t21 + t11 * _F(75.0)) * t1
    t14 = (t21 + t8) * _F(10000.0)
    t12 = ((t10 + t8) * t16 + t10 * t8) * _F(10000.0) + t6 * (t8 + _F(10000.0)) + t16 * t8 * t10 + ((t9 + t12) * t7 + t9 * t12)
    local_bc = (t4 * _F(10000.0) * t20) * (local_res8 * t1)
    local_b0 = local_res8 * t4 * t17
    local_c0 = local_bc * _F(24.0)
    local_bc = local_bc * _F(8.0)
    t18 = param_7 * param_7
    t19 = t18 * param_7
    t11 = (((t2 + _F(1.0)) * t21 + t15) * t4 + t20 * t1) * _F(20000.0) * t18
    t15 = (((t2 * t13 + t5) * t21 + t15 * _F(75.0)) * t1 + (t21 + t8) * local_res8) * (t4 * _F(10000.0)) * _F(4.0) * param_7
    t8 = t19 * t14
    t14 = t14 * _F(3.0) * t19
    local_c8 = (t11 + t8) + (t15 + local_bc)
    local_bc = t8 - t11 + t15 - local_bc
    local_c4 = t14 + t11 - t15 - local_c0
    local_c0 = t14 - t11 - t15 + local_c0
    local_ac = local_b0 * _F(8.0)
    local_b0 = local_b0 * _F(24.0)
    t8 = t3 * _F(3.0) * t19
    param_7 = (((((t13 + t10) * t16 + t13 * t10) * _F(10000.0) + (t9 + t5) * t7 + ((t6 * (t13 + _F(10000.0)) + t16 * t10 * t13) + t9 * t5)) * t21 + t12 * _F(75.0)) * t1 + t3 * local_res8) * t4 * _F(4.0) * param_7
    t18 = (((t6 + t16 * t10 + t2 * _F(10000.0) + (t9 + t7)) * t21 + t12) * (t4 + t4) + t17 + t17) * t18
    local_b8 = (t18 + t3 * t19) + (param_7 + local_ac)
    local_ac = t3 * t19 - t18 + param_7 - local_ac
    local_b4 = t8 + t18 - param_7 - local_b0
    local_b0 = t8 - t18 - param_7 + local_b0
    return _normalize((local_b8, local_b4, local_b0, local_ac), (local_c8, local_c4, local_c0, local_bc), _F(12))

def _vintage_mid(band, index, gain, rate):
    param_3 = _F(gain)
    param_4 = _F(1) / _F(rate)
    t8 = _F(5000.0) - param_3 * _F(312.4375)
    t4 = param_3 * _F(312.4375) + _F(5000.0)
    if band == 'low-mid':
        table = ((_F(1e-08), -_F(688160000000.0), -_F(1376320000000.0), _F(688160000000.0), _F(1376320000000.0)), (_F(5.8e-09), -_F(500479980000.0), -_F(1000959970000.0), _F(500479980000.0), _F(1000959970000.0)), (_F(3.3e-09), -_F(312800020000.0), -_F(625600040000.0), _F(312800020000.0), _F(625600040000.0)))
    else:
        table = ((_F(1e-07), -_F(6256000000000.0), -_F(12512000000000.0), _F(6256000000000.0), _F(12512000000000.0)), (_F(4.7e-08), -_F(3128000000000.0), -_F(6256000000000.0), _F(3128000000000.0), _F(6256000000000.0)), (_F(2.2e-08), -_F(1407599900000.0), -_F(2815199800000.0), _F(1407599900000.0), _F(2815199800000.0)))
    t5, t6, t9, t7, t1 = map(_F, table[index])
    t3 = param_4 * param_4
    t2 = t4 * _F(6800.0)
    local_c4 = t3 * -_F(1564000000000.0) - t9 * t5
    t4 = (((-_F(15000.0) - t8 - _F(6800.0)) * t5 * _F(63920000.0) - t5 * _F(524144000000.0)) * t4 - t5 * _F(63920000.0) * (t8 * _F(6800.0)) + ((-_F(15000.0) - t8) * t5 * _F(13600.0) - t5 * _F(111520000.0)) * t2) * param_4
    local_c8 = t4 + t6 * t5 + t3 * -_F(782000000000.0)
    local_c0 = t6 * t5 - t4 + t3 * -_F(782000000000.0)
    param_4 = ((t8 + _F(6800.0)) * t2 * _F(4700.0) + t8 * _F(958800000000.0) + (t2 + _F(157760000.0)) * (t8 * _F(6800.0))) * (t5 + t5) * param_4
    local_b8 = t7 * t5 + param_4 + t3 * _F(782000000000.0)
    local_b0 = t7 * t5 - param_4 + t3 * _F(782000000000.0)
    local_b4 = t3 * _F(1564000000000.0) - t1 * t5
    return _normalize((local_b8, local_b4, local_b0), (local_c8, local_c4, local_c0), _F(-1))

def _vintage_high(gain, rate):
    param_2 = _F(gain)
    local_res20 = _F(1) / _F(rate)
    t12 = _F(5000.0) - param_2 * _F(312.4375)
    t4 = param_2 * _F(312.4375) + _F(5000.0)
    t6 = t4 * _F(620.0)
    t5 = t4 + _F(620.0)
    t9 = (-_F(620.0) - t4) * _F(620.0)
    t11 = (-_F(620.0) - t4) * _F(5100.0) - t6
    t7 = t5 * _F(5100.0) + t6
    t2 = t11 * _F(5100.0) - t12 * t7
    t1 = t12 * _F(0.00018876) + _F(0.104346)
    t14 = (t4 + _F(5100.0)) * _F(6200.0)
    t3 = (t4 * _F(17720.0) + _F(64362000.0) + t14) * _F(145700000.0)
    t15 = ((t14 * _F(1116250000.0) + t3) + ((t4 + _F(5100.0)) * _F(3423949800000.0) + t3)) * _F(3.3e-08)
    t3 = (t11 * _F(6200.0) - t7 * _F(12000.0)) * _F(145700000.0)
    t16 = ((t9 - t5 * _F(12000.0)) * _F(5100.0) - t6 * _F(12620.0) + t11 * _F(5100.0)) * _F(145700000.0)
    t13 = -_F(2.6352235e+19) - t12 * _F(5167105000000000.0) - (t12 + _F(5100.0)) * _F(1.0000849e+16)
    t10 = -_F(9.988347e+19) - t12 * _F(1.9584995e+16)
    t14 = ((-_F(12620.0) - t12) * _F(5100.0) - t12 * _F(12620.0)) * _F(833404000000.0)
    t4 = t2 * _F(3423949800000.0)
    t17 = (t2 * _F(6200.0) - t7 * _F(12000.0) * (t12 + _F(5100.0))) * _F(145700000.0)
    t8 = t15 * t1
    t2 = ((t9 * _F(5100.0) - (t12 + _F(12000.0)) * t5 * _F(5100.0) - (t12 + _F(12620.0)) * t6) * _F(5100.0) - t7 * (t12 * _F(12620.0))) * _F(145700000.0)
    t4 = (t17 + t17 + t4) + (t2 + t4 + t2)
    t5 = local_res20 * local_res20
    t2 = t4 * _F(4.356e-15)
    local_cc = t5 * -_F(1.9808346e+17) - t4 * _F(8.712e-15)
    t4 = (t15 * _F(11440.0) + t1 * _F(34629977000000.0)) * local_res20
    local_res20 = (t3 * _F(6.6e-08) + t3 * _F(6.6e-08) + t11 * _F(3423949800000.0) * _F(6.6e-08) + (t11 * _F(3423949800000.0) + t16 + t16) * _F(6.6e-08) + (t14 * _F(6.6e-08) + t14 * _F(6.6e-08) + t10 * _F(6.6e-08) + (t13 + t10 + t13) * _F(6.6e-08))) * local_res20
    t1 = t8 * _F(4.0)
    local_d0 = local_res20 + t2 + t5 * -_F(9.904173e+16)
    local_c8 = t2 - local_res20 + t5 * -_F(9.904173e+16)
    local_bc = t5 * _F(1.9808346e+17) - t8 * _F(8.0)
    local_c0 = t4 + t1 + t5 * _F(9.904173e+16)
    local_b8 = t1 - t4 + t5 * _F(9.904173e+16)
    return _normalize((local_c0, local_bc, local_b8), (local_d0, local_cc, local_c8), _F(-1))

def _vintage_low(index, gain, rate):
    if rate > 176400:
        raise ValueError('Vintage EQ supports sample rates up to 176400 Hz; io24 operates at 44100/48000/88200/96000 Hz')
    param_3 = _F(gain)
    param_5 = _F(1) / _F(rate)
    t6 = _F(23500.0) - param_3 * _F(1439.375)
    t2 = param_3 * _F(1439.375) + _F(23500.0)
    t4 = _F((_F(2e-07), _F(1e-07), _F(4.7e-08), _F(1.5e-08))[index])
    t5 = t2 + _F(6200.0)
    t7 = t4 * _F(6200.0)
    local_d8 = t5 * -_F(11440.0)
    t3 = t2 * t4
    local_d4 = t2 * t7 * -_F(11440.0) - t5 * (t4 * t6) * _F(11440.0) - ((t2 * _F(8.58e-05) + _F(1.5615599)) * t6 + t2 * _F(2.052336) + _F(19108.002))
    local_d0 = (((t7 * -_F(5720.0) - t4 * _F(169998400.0) + t7 * -_F(5720.0)) * t2 - t4 * _F(1273866900000.0)) * t6 + t3 * -_F(1273866900000.0)) * _F(1.5e-08) - t2 * t7 * _F(11440.0) * (t4 * t6)
    local_cc = t6 * (t3 * -_F(1273866900000.0)) * (t4 * _F(1.5e-08))
    local_c8 = t6 * _F(11440.0) + _F(70928000.0)
    local_c4 = ((t5 + _F(17720.0)) * t6 * _F(8.58e-05) + (t2 * _F(1.5615599) + _F(19108.002))) + ((t3 + t7) * t6 * _F(11440.0) + t3 * _F(70928000.0))
    local_bc = t2 * _F(19108.002) * t6 * (t4 * t4)
    local_c0 = ((t4 * _F(29720.0) + t7 + t7) * t2 + t4 * _F(222704000.0)) * t6 * _F(8.58e-05) + t3 * _F(19108.002) + (t6 * t7) * (t3 * _F(11440.0))
    return _normalize(_bilinear3((local_c8, local_c4, local_c0, local_bc), param_5), _bilinear3((local_d8, local_d4, local_d0, local_cc), param_5), _F(-1))

def vintage(band, index, gain, rate):
    if band == 'low':
        return _vintage_low(index, gain, rate)
    if band == 'high':
        return _vintage_high(gain, rate)
    if band in ('low-mid', 'hi-mid'):
        return _vintage_mid(band, index, gain, rate)
    raise ValueError('unknown Vintage band %r' % band)
