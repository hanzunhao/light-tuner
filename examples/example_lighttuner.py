import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from light_tuner import log_metrics
from sklearn.metrics import confusion_matrix, precision_recall_curve
import numpy as np

params = {
    "epochs": 3,
    "learning_rate": 1e-3,
    "batch_size": 64
}

# 定义设备
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# 定义模型
class NeuralNetwork(nn.Module):
    def __init__(self):
        super().__init__()
        self.flatten = nn.Flatten()
        self.linear_relu_stack = nn.Sequential(
            nn.Linear(28 * 28, 512),
            nn.ReLU(),
            nn.Linear(512, 512),
            nn.ReLU(),
            nn.Linear(512, 10),
        )

    def forward(self, x):
        x = self.flatten(x)
        logits = self.linear_relu_stack(x)
        return logits


# 加载和准备数据
transform = transforms.Compose(
    [transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))]
)
train_dataset = datasets.MNIST("../data", train=True, download=True,
                               transform=transform)
test_dataset = datasets.MNIST("../data", train=False, transform=transform)
train_loader = DataLoader(train_dataset, batch_size=params["batch_size"], shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=1000)

# 初始化模型
model = NeuralNetwork().to(device)

# 定义优化器和损失函数
loss_fn = nn.CrossEntropyLoss()
optimizer = optim.SGD(model.parameters(), lr=params["learning_rate"])

# 训练循环
for epoch in range(params["epochs"]):
    model.train()
    train_loss, correct, total = 0, 0, 0
    # 批次训练
    for batch_idx, (data, target) in enumerate(train_loader):
        data, target = data.to(device), target.to(device)

        # 前向传播
        optimizer.zero_grad()
        output = model(data)
        loss = loss_fn(output, target)

        # 反向传播
        loss.backward()
        optimizer.step()

        # 计算指标
        train_loss += loss.item()
        _, predicted = output.max(1)
        total += target.size(0)
        correct += predicted.eq(target).sum().item()

        # 记录批次指标（每100个批次）
        if batch_idx % 100 == 0:
            batch_loss = train_loss / (batch_idx + 1)
            batch_acc = 100.0 * correct / total

    # 计算epoch指标
    epoch_loss = train_loss / len(train_loader)
    epoch_acc = 100.0 * correct / total
    log_metrics(
        {
            "train_loss": epoch_loss,
            "train_acc": epoch_acc
        },
        epoch=epoch,
        tag="train"
    )

    # --- 验证部分 (增加数据采集用于计算 Matrix/Array) ---
    model.eval()
    val_loss, val_correct = 0, 0
    all_preds = []
    all_targets = []
    all_probs = []  # 用于计算 PR/ROC 曲线的概率值
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)

            # 收集数据
            prob = torch.softmax(output, dim=1)
            _, predicted = output.max(1)

            loss = loss_fn(output, target)

            all_preds.extend(predicted.cpu().numpy())
            all_targets.extend(target.cpu().numpy())
            all_probs.extend(prob.cpu().numpy())

            val_loss += loss_fn(output, target).item()

    # 1. 计算基础 Scalar 指标
    val_acc = 100.0 * np.sum(np.array(all_preds) == np.array(all_targets)) / len(all_targets)
    log_metrics(
        {
            "val_loss": val_loss / len(test_loader),
            "val_acc": val_acc
        },
        epoch=epoch,
        tag="val"
    )

    # 2. 计算混淆矩阵 (Matrix)
    # 得到一个 10x10 的二维数组
    cm = confusion_matrix(all_targets, all_preds).tolist()
    log_metrics(
        {"confusion_matrix": cm},
        epoch=epoch,
        tag="val"
    )

    # 3. 计算 PR 曲线数据 (Array)
    # 针对多分类，我们取其中一类（比如类别 0）作为代表展示曲线
    # 或者计算所有类别的平均值。这里以类别 0 为例：
    all_probs = np.array(all_probs)
    all_targets_np = np.array(all_targets)

    # 获取类别0的 precision, recall
    precision, recall, _ = precision_recall_curve((all_targets_np == 0).astype(int), all_probs[:, 0])

    # 构造前端易读的坐标对数组：[[r1, p1], [r2, p2], ...]
    pr_data = np.stack([recall, precision], axis=1).tolist()

    # 为了防止数据点过多导致数据库过大，可以进行降采样（每10个取1个）
    pr_data_sampled = pr_data[::10]

    log_metrics(
        {
            "pr_curve_class_0": pr_data_sampled
        },
        epoch=epoch,
        tag="val"
    )
