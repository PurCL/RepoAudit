# MagickCore

Project Repo: https://github.com/ImageMagick/ImageMagick/tree/6e167ed083e252cb318b4db3316854be80de1693/MagickCore

## Case 1

Is Reproduce: Yes

Program locations:

* https://github.com/ImageMagick/ImageMagick/tree/6e167ed083e252cb318b4db3316854be80de1693/MagickCore/threshold.c#L2075

Bug traces:

* <  random_info=AcquireRandomInfoThreadSet();, RandomThresholdImage>

Explanation:

* The NULL value from AcquireRandomInfoThreadSet at line 43 is deferenced without null check.


## Case 2

Is Reproduce: Yes

Program locations:

* https://github.com/ImageMagick/ImageMagick/tree/6e167ed083e252cb318b4db3316854be80de1693/MagickCore/morphology.c#L2336
* https://github.com/ImageMagick/ImageMagick/tree/6e167ed083e252cb318b4db3316854be80de1693/MagickCore/morphology.c#L4228

Bug traces:

* <  clone = CloneKernelInfo(last);, ExpandMirrorKernelInfo>
* <kernel, RotateKernelInfo>

Explanation:

* The NULL value of pointer `clone` at line 9 is passed as the first argument to RotateKernelInfo at line 10.
* The NULL value of pointer `kernel` at line 1 is dereferenced at line 4 without any NULL check.


## Case 3

Is Reproduce: Yes

Program locations:

* https://github.com/ImageMagick/ImageMagick/tree/6e167ed083e252cb318b4db3316854be80de1693/MagickCore/morphology.c#L2424
* https://github.com/ImageMagick/ImageMagick/tree/6e167ed083e252cb318b4db3316854be80de1693/MagickCore/morphology.c#L4228

Bug traces:

* <    clone = CloneKernelInfo(last);, ExpandRotateKernelInfo>
* <kernel, RotateKernelInfo>

Explanation:

* NULL value from CloneKernelInfo propagates to first argument of RotateKernelInfo at line 12
* The NULL value of pointer `kernel` at line 1 is dereferenced at line 4 without any NULL check.


## Case 4

Is Reproduce: Yes

Program locations:

* https://github.com/ImageMagick/ImageMagick/tree/6e167ed083e252cb318b4db3316854be80de1693/MagickCore/morphology.c#L2424
* https://github.com/ImageMagick/ImageMagick/tree/6e167ed083e252cb318b4db3316854be80de1693/MagickCore/morphology.c#L2387

Bug traces:

* <    clone = CloneKernelInfo(last);, ExpandRotateKernelInfo>
* <kernel2, SameKernelInfo>

Explanation:

* NULL value from CloneKernelInfo propagates to second argument of SameKernelInfo at line 13
* The NULL value of pointer `kernel2` from parameter is dereferenced at line 8 without any null check.


## Case 5

Is Reproduce: Yes

Program locations:

* https://github.com/ImageMagick/ImageMagick/tree/6e167ed083e252cb318b4db3316854be80de1693/MagickCore/statistic.c#L506

Bug traces:

* <  random_info=AcquireRandomInfoThreadSet();, EvaluateImages>

Explanation:

* The NULL value of pointer `random_info` at line 63 is deferenced at line 68.


## Case 6

Is Reproduce: Yes

Program locations:

* https://github.com/ImageMagick/ImageMagick/tree/6e167ed083e252cb318b4db3316854be80de1693/MagickCore/effect.c#L3800

Bug traces:

* <  random_info=AcquireRandomInfoThreadSet();, SpreadImage>

Explanation:

* The NULL value from AcquireRandomInfoThreadSet at line 58 is dereferenced without check.


## Case 7

Is Reproduce: Yes

Program locations:

* https://github.com/ImageMagick/ImageMagick/tree/6e167ed083e252cb318b4db3316854be80de1693/MagickCore/effect.c#L3800
* https://github.com/ImageMagick/ImageMagick/tree/6e167ed083e252cb318b4db3316854be80de1693/MagickCore/random-private.h#L40

Bug traces:

* <  random_info=AcquireRandomInfoThreadSet();, SpreadImage>
* <random_info, DestroyRandomInfoThreadSet>

Explanation:

* NULL `random_info` is passed as argument to DestroyRandomInfoThreadSet at line 115.\nThe NULL value of `random_info` is dereferenced at line 9 in the loop without a NULL check.


## Case 8

Is Reproduce: Yes

Program locations:

* https://github.com/ImageMagick/ImageMagick/tree/6e167ed083e252cb318b4db3316854be80de1693/MagickCore/fx.c#L322

Bug traces:

* <  random_info=AcquireRandomInfoThreadSet();, AddNoiseImage>

Explanation:

* The NULL value from AcquireRandomInfoThreadSet at line 57 is dereferenced without check.


## Case 9

Is Reproduce: Yes

Program locations:

* https://github.com/ImageMagick/ImageMagick/tree/6e167ed083e252cb318b4db3316854be80de1693/MagickCore/fx.c#L322
* https://github.com/ImageMagick/ImageMagick/tree/6e167ed083e252cb318b4db3316854be80de1693/MagickCore/random-private.h#L40

Bug traces:

* <  random_info=AcquireRandomInfoThreadSet();, AddNoiseImage>
* <random_info, DestroyRandomInfoThreadSet>

Explanation:

* The NULL value of `random_info` at line 57 is passed as an argument to DestroyRandomInfoThreadSet at line 137.\nThe NULL value of `random_info` is dereferenced at line 9 in the loop without a NULL check.


