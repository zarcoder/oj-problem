#include <cstdio>
#include <vector>
#include <algorithm>
#include <functional>
using namespace std;

int main() {
    int m;
    scanf("%d", &m);
    if (m <= 0) {
        int n;
        scanf("%d", &n);
        while (n--) printf("-1\n");
        return 0;
    }
    
    vector<int> nums(m);
    for (int i = 0; i < m; ++i) 
        scanf("%d", &nums[i]);
    
    sort(nums.begin(), nums.end(), greater<>());
    
    const auto binary_search = [&nums, m](int q) {
        int l = 0, r = m - 1;
        while (l <= r) {
            int mid = (l + r) >> 1;
            if (nums[mid] == q) return mid + 1;
            nums[mid] > q ? l = mid + 1 : r = mid - 1;
        }
        return -1;
    };
    
    int n;
    scanf("%d", &n);
    while (n--) {
        int q;
        scanf("%d", &q);
        printf("%d\n", binary_search(q));
    }
    
    return 0;
}