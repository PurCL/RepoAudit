var a = console.error;
delete a.error;
const exec = function () {
    a.error();
}
exec()