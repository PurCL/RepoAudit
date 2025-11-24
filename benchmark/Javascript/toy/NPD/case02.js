function func_generator(value) {
    let fn = null;
    if (value % 3 == 0) {
        fn = console.log;
    } else if (value % 3 == 1) {
        fn = console.error;
    }
    return fn;
}

const print = () => {
    func_generator(8)("Hello world!");
    console.log("Done");
}
