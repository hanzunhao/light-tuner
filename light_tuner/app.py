from datetime import datetime
from typing import Any
from flask import Flask, request, jsonify
from flask_cors import CORS
from light_tuner.utils.logger import logger
from light_tuner.storage.sqlite_manager import db_manager  # 根据实际路径调整
import json

# 初始化 Flask 应用
app = Flask(__name__)
# 允许跨域
CORS(app, resources=r"/*")


# -------------------------- 通用工具函数 --------------------------
def success_response(data: Any = None, msg: str = "操作成功"):
    """通用成功响应格式"""
    return jsonify({
        "code": 200,
        "msg": msg,
        "data": data
    })


def error_response(msg: str = "操作失败", code: int = 500):
    """通用错误响应格式"""
    return jsonify({
        "code": code,
        "msg": msg,
        "data": None
    })


def parse_datetime(date_str: str) -> datetime:
    """解析时间字符串为 datetime 对象"""
    return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")


# -------------------------- Experiment 相关接口 --------------------------

# 查询接口
@app.route("/api/experiment", methods=["GET"])
def get_experiments():
    try:
        # 1. 从请求参数中获取查询条件（均为可选参数）
        name = request.args.get("name")
        status = request.args.get("status")
        search_mode = request.args.get("search_mode")

        # 2. 从请求参数中获取排序参数（设置默认值，兼容前端不传的情况）
        sort_by = request.args.get("sort_by", "start_time")
        sort_order = request.args.get("sort_order", "DESC")

        # 3. 调用数据库方法执行查询
        experiments = db_manager.select_experiments(
            name=name,
            status=status,
            search_mode=search_mode,
            sort_by=sort_by,
            sort_order=sort_order
        )

        # 4. 返回成功响应
        return success_response(
            data=experiments,
            msg=f"查询成功，共返回 {len(experiments)} 条记录"
        )

    except Exception as e:
        return error_response(f"服务器内部错误：{str(e)}")


# -------------------------- Test 相关接口 --------------------------
# 查询指定实验id下的所有测试记录
@app.route("/api/test", methods=["GET"])
def get_tests():
    experiment_id = request.args.get("experiment_id")
    try:
        tests = db_manager.select_test_by_experiment_id(experiment_id)
        return success_response(
            data=tests,
            msg=f"查询成功，共返回 {len(tests)} 条记录"
        )
    except Exception as e:
        return error_response(f"服务器内部错误：{str(e)}")


# -------------------------- Metric 相关接口 --------------------------
# 查询指定测试id下的所有指标记录
@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    # 1. 获取 test_id_list 字符串 (例如 "1,2,3")
    test_id_list_str = request.args.get("test_id_list")
    if not test_id_list_str:
        return error_response("缺少必填参数: test_id_list", code=400)

    try:
        # 2. 将字符串解析为整数列表 [1, 2, 3]
        try:
            test_id_list = [int(tid.strip()) for tid in test_id_list_str.split(",") if tid.strip()]
        except ValueError:
            return error_response("参数格式错误: test_id_list 应为逗号分隔的数字", code=400)

        if not test_id_list:
            return error_response("test_id_list 不能为空", code=400)

        # 3. 获取可选过滤参数
        metric_name = request.args.get("metric_name")
        tag = request.args.get("tag")
        data_type = request.args.get("data_type")

        # 4. 调用刚才修改的数据库方法 (支持 test_id_list)
        metrics = db_manager.select_metrics(
            test_id_list=test_id_list,
            metric_name=metric_name,
            tag=tag,
            data_type=data_type
        )

        # 5. 数据转换处理
        for m in metrics:
            if m.get('data_type') in ['matrix', 'array', 'json']:
                try:
                    m['value'] = json.loads(m['value'])
                except Exception:
                    pass

        return success_response(
            data=metrics,
            msg=f"成功获取来自 {len(test_id_list)} 个测试的 {len(metrics)} 条指标记录"
        )

    except Exception as e:
        logger.error(f"查询指标异常: {str(e)}")
        return error_response(f"服务器内部错误：{str(e)}")


# -------------------------- 启动服务 --------------------------
if __name__ == "__main__":
    # 开发环境配置：调试模式开启，端口8080，允许外部访问
    app.run(
        host="0.0.0.0",  # 允许局域网/外网访问
        port=8080,  # 端口号
        debug=True  # 调试模式（生产环境需关闭）
    )
