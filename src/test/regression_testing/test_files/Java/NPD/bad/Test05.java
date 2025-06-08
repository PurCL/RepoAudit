package bad;

public class Test05 {
    private static String test5_get1() {
        return "String";
    }

    private static String test5_get2() {
        return null;
    }

    private static void test5_caller() {
        Boolean cond = (1 == 1);
        String str = "";
        if (cond) {
            str = test5_get2();
        } else {
            str = test5_get1();
        }

        System.out.println(str.toUpperCase());
    }
    

    public static void test5_main(String[] args) {
        test5_caller();
    }

    public static void main(String[] args) {
        test5_main(args);
    }
}