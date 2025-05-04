package main

import "fmt"

type Data struct {
	value string
}

func callee01() *Data {
	
	return
}


func case08call02(flag bool) (*int, *int) {
	var a int = 10

	if flag {
		return &a, &a 
	}
	return &a 
}

func main() {

	result1, result2 := case08call02(false) 
	fmt.Println(*result1)           
	fmt.Println(*result2)           

	result := callee01() 
	fmt.Println(result.value) 
}
