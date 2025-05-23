package main

import (
	"fmt"
)

type Counter struct {
	value *int
}

func (c *Counter) Increment(amount int) int {
	*c.value += amount
	return *c.value
}

func main() {
	initialValue := 10
	counter_1 := Counter{value: &initialValue}
	counter_2 := Counter{value: nil}

	newValue_1 := counter_1.Increment(1)
	newValue_2 := counter_2.Increment(2)

	fmt.Println("New values:", newValue_1, newValue_2)
}
