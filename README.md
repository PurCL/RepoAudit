# Bugs Detected By *RepoAudit*

## Memory Leak

Find a path starting from malloc-like API and not containing any free-like API.

* [net_4cd8371](ML/C_net_4cd8371.md)
* [memcached](ML/C_memcached.md)
* [sound_1c4f29e](ML/C_sound_1c4f29e.md)
* [libsass](ML/C++_libsass.md)
* [mm_73b73ba](ML/C_mm_73b73ba.md)

## Null Pointer Dereference

Find a path starting from null value and ending at the dereference.

* [MagickCore](NPD/C_MagickCore.md)
* [libfreenect](NPD/C_libfreenect.md)
* [openldap](NPD/C_openldap.md)
* [coturn_server](NPD/C_coturn_server.md)
* [sofa-pbrpc](NPD/C++_sofa-pbrpc.md)

## Use After Free

Find a path starting from free-like API and ending at free-like API or other usages (e.g, dereference).

* [redis](UAF/C_redis.md)
* [i18n](UAF/C++_i18n.md)
* [shadowsocks-libev](UAF/C_shadowsocks-libev.md)
* [peci_e79b548](UAF/C_peci_e79b548.md)
* [wabt_tools](UAF/C++_wabt_tools.md)

