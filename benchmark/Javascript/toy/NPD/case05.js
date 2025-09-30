var a = console.error;
delete a.error;

function exec() {
    a.error();
}