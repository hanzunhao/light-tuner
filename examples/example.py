import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

# 训练参数
params = {
    "epochs": 3,
    "learning_rate": 1e-3,
    "batch_size": 64,
    "optimizer": "SGD",
    "model_type": "MLP",
    "hidden_units": [512, 512],
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
# todo:转为使用相对路径
train_dataset = datasets.MNIST("D:\\Program Files\\Code\\Python\\light-tuner\\data", train=True, download=True,
                               transform=transform)
test_dataset = datasets.MNIST("D:\\Program Files\\Code\\Python\\light-tuner\\data", train=False, transform=transform)
train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
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

    # 验证
    model.eval()
    val_loss, val_correct, val_total = 0, 0, 0
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            loss = loss_fn(output, target)

            val_loss += loss.item()
            _, predicted = output.max(1)
            val_total += target.size(0)
            val_correct += predicted.eq(target).sum().item()

    # 计算并记录验证指标
    val_loss = val_loss / len(test_loader)
    val_acc = 100.0 * val_correct / val_total

    # 打印训练进度
    print(
        f"Epoch {epoch + 1}/{params['epochs']}, "
        f"训练损失: {epoch_loss:.4f}, 训练准确率: {epoch_acc:.2f}%, "
        f"验证损失: {val_loss:.4f}, 验证准确率: {val_acc:.2f}%"
    )
