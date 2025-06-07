package main

func variadicNilable(a, b, c *int, d *int, e ...*int) int {
	if len(e) >= 2 {
		return *e[1]
	}
	return *a
}

func main() {
	var x int = 1
	variadicNilable(nil, &x, &x, &x)
	variadicNilable(&x, &x, &x, &x)
	variadicNilable(&x, &x, &x, &x, nil)
	variadicNilable(&x, &x, &x, &x, &x, nil)
	variadicNilable(nil, &x, &x, &x, &x, &x)
}
