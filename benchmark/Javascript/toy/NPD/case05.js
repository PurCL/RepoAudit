function func(value) {
    return func2(value);
}

function func2(value) {
    console.log(+value.prop);
    delete value.prop;
    return value;
}

const printprop = () => {
	let d = {
        prop: "1"
    };
    d = func(d);
    console.log(d.prop.length);
}