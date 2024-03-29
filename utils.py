import torch
from torchvision.datasets import CIFAR100, CIFAR10
from torch.utils.data import Dataset
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms as transforms
import torchvision.datasets as datasets
from torchvision.datasets import CIFAR100
import torch.nn.functional as F
from torch.utils.data import DataLoader, Subset, random_split
import optuna


class FilteredCIFAR100(Dataset):
    def __init__(self, cifdataset, cifar10_labels, transform=None):
        self.data = []
        self.targets = []
        self.transform = transform

        # Filter out samples whose labels are not present in CIFAR-10
        for idx, (image, label) in enumerate(cifdataset):
            if label not in cifar10_labels:
                self.data.append(image)
                self.targets.append(label)

    def __getitem__(self, index):
        image, label = self.data[index], self.targets[index]

        if self.transform:
            image = self.transform(image)

        return image, label

    def __len__(self):
        return len(self.data)


# Define transformations
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
])

# Load CIFAR-100 and CIFAR-10 datasets
cifar100_dataset = CIFAR100(root='./datafil', train=True, download=True)
cifar100_test = CIFAR100(root='./datafil', train=False, download=True)
cifar10_dataset = CIFAR10(root='./datafil', train=True, download=True)

# Get the labels present in CIFAR-10
cifar10_labels = set(cifar10_dataset.targets)

# Create FilteredCIFAR100 datasets with transformations
train_dataset = FilteredCIFAR100(
    cifar100_dataset, cifar10_labels, transform=transform)
test_dataset = FilteredCIFAR100(
    cifar100_test, cifar10_labels, transform=transform)
# Split the dataset into training and validation sets (80% training, 20% validation)
train_size = int(0.2 * len(train_dataset))
val_size = len(train_dataset) - train_size
train_dataset, _ = random_split(train_dataset, [train_size, val_size])

# Create data loaders for training and validation
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)

print("Number of samples in filtered CIFAR-100 dataset:",
      len(train_dataset))

print("Number of samples in filtered CIFAR-100 dataset test:",
      len(test_dataset))


class Network(nn.Module):
    def __init__(self):
        super(Network, self).__init__()

        self.conv1 = nn.Conv2d(
            in_channels=3, out_channels=12, kernel_size=5, stride=1, padding=1)
        self.bn1 = nn.BatchNorm2d(12)
        self.conv2 = nn.Conv2d(
            in_channels=12, out_channels=12, kernel_size=5, stride=1, padding=1)
        self.bn2 = nn.BatchNorm2d(12)
        self.pool = nn.MaxPool2d(2, 2)
        self.conv4 = nn.Conv2d(
            in_channels=12, out_channels=24, kernel_size=5, stride=1, padding=1)
        self.bn4 = nn.BatchNorm2d(24)
        self.conv5 = nn.Conv2d(
            in_channels=24, out_channels=24, kernel_size=5, stride=1, padding=1)
        self.bn5 = nn.BatchNorm2d(24)
        self.fc1 = nn.Linear(24*10*10, 10)

    def forward(self, input):
        output = F.relu(self.bn1(self.conv1(input)))
        output = F.relu(self.bn2(self.conv2(output)))
        output = self.pool(output)
        output = F.relu(self.bn4(self.conv4(output)))
        output = F.relu(self.bn5(self.conv5(output)))
        output = output.view(-1, 24*10*10)
        output = self.fc1(output)

        return output


# Load pre-trained model
# Load the model's state dictionary
model = Network()
model.load_state_dict(torch.load('model/model.pth'))

# Access the fc1 layer attribute
num_ftrs = model.fc1.in_features
# Modify last layer for 100 classes in CIFAR-100
model.fc1 = nn.Linear(num_ftrs, 100)


# Define loss function and optimizer
criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(model.parameters(), lr=0.001, momentum=0.9)
# Function to save the model


def saveModel():
    path = "./model/model_case3.pth"
    torch.save(model.state_dict(), path)


def fine_tuning(num_epochs):
    # Fine-tuning loop
    for epoch in range(num_epochs):
        # Training phase
        running_loss = 0.0
        for inputs, labels in train_loader:
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
        print(
            f"Epoch {epoch+1}, Training Loss: {running_loss/len(train_loader)}")

        # Validation phase (compute test accuracy)
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, labels in test_loader:
                outputs = model(inputs)
                _, predicted = torch.max(outputs, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()

        test_accuracy = 100 * correct / total
        print(f"Epoch {epoch+1}, Test Accuracy: {test_accuracy:.2f}%")


if __name__ == "__main__":
    fine_tuning(10)
    saveModel()


# Specify the Learning Rate Search Space:
trial = study.ask()
learning_rate = trial.suggest_loguniform("learning_rate", 1e-5, 1e-1)

# run optimize
study = optuna.create_study(direction="minimize")
study.optimize(objective_function, n_trials=100)
