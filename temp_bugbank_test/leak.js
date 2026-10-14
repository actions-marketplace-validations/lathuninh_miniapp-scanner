// 测试信息泄露
const API_BASE = "https://api.example.com/admin/users";
const test_user = { test_user: "admin", test_password: "123456" };

Page({
  data: {
    debug: true,
    isDebug: true,
  },
  onLoad() {
    const path = "/api/internal/debug";
    console.log(path);
  }
});
