package bad;
public class Test01 {
    public static Object test1_getObj() {
        return null;
    }
    public static int test1_useObj() {
        Object obj = test1_getObj();
        return obj.hashCode();
    }
    public static void test1_main(String[] args) {
        System.out.println(test1_useObj());
    }
}