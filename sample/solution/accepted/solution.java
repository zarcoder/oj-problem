import java.util.*;
import java.io.*;

public class Solution {
    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        PrintWriter pw = new PrintWriter(System.out);
        
        // 读取输入数据
        int m = Integer.parseInt(br.readLine().trim());
        String[] numbersStr = br.readLine().trim().split(" ");
        
        int[] numbers = new int[m];
        for (int i = 0; i < m; i++) {
            numbers[i] = Integer.parseInt(numbersStr[i]);
        }
        
        // 创建一个副本用于排序
        Integer[] sortedNumbers = new Integer[m];
        for (int i = 0; i < m; i++) {
            sortedNumbers[i] = numbers[i];
        }
        
        // 从大到小排序
        Arrays.sort(sortedNumbers, Collections.reverseOrder());
        
        // 创建一个映射，存储每个数字在排序后的位置（1开始计数）
        Map<Integer, Integer> positions = new HashMap<>();
        for (int i = 0; i < m; i++) {
            positions.put(sortedNumbers[i], i + 1);
        }
        
        // 处理查询
        int n = Integer.parseInt(br.readLine().trim());
        for (int i = 0; i < n; i++) {
            int query = Integer.parseInt(br.readLine().trim());
            
            // 查找位置
            if (positions.containsKey(query)) {
                pw.println(positions.get(query));
            } else {
                pw.println("-1");
            }
        }
        
        pw.flush();
        pw.close();
        br.close();
    }
} 