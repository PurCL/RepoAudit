package main

import "fmt"

func test8_called() *int {
	return new(int)
}

func test8_main() {
	p := test8_called()
	*p = 42
	fmt.Println(*p)
}

func main() {
	test8_main()
}