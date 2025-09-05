function process_data(myobj) {
    const inner_processing = (myobj) => {
        delete myobj.func;
        return myobj;
    }
    myobj.func("Hello");
    myobj = inner_processing(myobj);
    myobj.func("Hello");
}

function main() {
    let myobj = {
        func: console.log
    };
    process_data(myobj)
}