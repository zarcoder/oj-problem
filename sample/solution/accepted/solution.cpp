#include <iostream>
#include <vector>
#include <algorithm>
#include <unordered_map>
using namespace std;

void solve() {
    // 读取输入数据
    int m;
    cin >> m;
    
    vector<int> numbers(m);
    for (int i = 0; i < m; i++) {
        cin >> numbers[i];
    }
    
    // 创建一个副本用于排序
    vector<int> sorted_numbers = numbers;
    sort(sorted_numbers.begin(), sorted_numbers.end(), greater<int>()); // 从大到小排序
    
    // 创建一个映射，存储每个数字在排序后的位置（1开始计数）
    unordered_map<int, int> positions;
    for (int i = 0; i < m; i++) {
        positions[sorted_numbers[i]] = i + 1;
    }
    
    // 处理查询
    int n;
    cin >> n;
    
    for (int i = 0; i < n; i++) {
        int query;
        cin >> query;
        
        // 查找位置
        if (positions.find(query) != positions.end()) {
            cout << positions[query] << "\n";
        } else {
            cout << "-1\n";
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    // 取消注释以处理多个测试用例
    // int t;
    // cin >> t;
    // while (t--) {
        solve();
    // }
    
    return 0;
} 