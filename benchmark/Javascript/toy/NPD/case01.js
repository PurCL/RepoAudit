function test2_process(data) {
    let value = data[0];
    return value;
}
    

function test2_caller() {
    let data = null;
    return test2_process(data)
}
