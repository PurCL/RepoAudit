# shadowsocks-libev

Project Repo: https://github.com/shadowsocks/shadowsocks-libev/tree/8e52029d311df3880ffb1c5bea922f6e0e3cecdd

## Case 1

Is Reproduce: Yes

Program locations:

* https://github.com/shadowsocks/shadowsocks-libev/tree/8e52029d311df3880ffb1c5bea922f6e0e3cecdd/src/local.c#L857

Bug traces:

* <            close_and_free_remote(EV_A_ remote);, remote_recv_cb>

Explanation:

* The freed `remote` is dereferenced at line 72 via `setsockopt(remote->fd, ...)`.


