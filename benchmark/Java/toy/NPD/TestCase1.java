public public class TestCase1 {
    public static Object test1_getObj() {
        return null;
    }
    public static int test1_useObj() {
        Object obj = test1_getObj();
        return obj.hashCode();
    }
    
    public static void main(String[] args) {
        try {
            test1_useObj();
        } catch (Exception e) {
            System.out.println("Case 1 Exception: " + e);
        }
    }
}
