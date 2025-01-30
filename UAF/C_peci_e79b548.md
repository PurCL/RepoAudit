# peci_e79b548

Project Repo: https://github.com/torvalds/linux/tree/e79b548b7202bb3accdfe64f113129a4340bc2f9/drivers/peci

## Case 1

Is Reproduce: Yes

Program locations:

* https://github.com/torvalds/linux/tree/e79b548b7202bb3accdfe64f113129a4340bc2f9/drivers/peci/cpu.c#L191

Bug traces:

* <	auxiliary_device_uninit(adev);, adev_release>

Explanation:

* The pointer `adev` is freed by auxiliary_device_uninit at line 5, then dereferenced at line 7 to access the name field.


