var myname = "daniel";
myname = null;

function test2_process(data) {
    let current = myname;
    let value = data[0];
    console.log(current.length)
    return value;
}
    

function test2_caller() {
    let data = null;
    return test2_process(data)
}
