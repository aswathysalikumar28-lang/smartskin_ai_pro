import sys
print("Python version:", sys.version)

try:
    import numpy as np
    print("numpy OK")
except Exception as e:
    print("numpy ERROR:", e)
    sys.exit()

try:
    import cv2
    print("cv2 OK")
except Exception as e:
    print("cv2 ERROR:", e)
    sys.exit()

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    print("torch OK:", torch.__version__)
except Exception as e:
    print("torch ERROR:", e)
    sys.exit()

try:
    from sklearn.model_selection import train_test_split
    print("sklearn OK")
except Exception as e:
    print("sklearn ERROR:", e)
    sys.exit()

IMG_SIZE = 64
EPOCHS = 20
BATCH_SIZE = 32

def generate_synthetic_data(n=400):
    X, y = [], []
    for label in range(3):
        for _ in range(n):
            img = np.zeros((IMG_SIZE, IMG_SIZE, 3), dtype=np.uint8)
            base_r = np.random.randint(180, 220)
            base_g = np.random.randint(140, 180)
            base_b = np.random.randint(100, 140)
            img[:, :] = [base_b, base_g, base_r]
            noise = np.random.randint(-20, 20, img.shape, dtype=np.int16)
            img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
            num_spots = [3, 10, 25][label]
            for _ in range(num_spots):
                x = np.random.randint(5, IMG_SIZE - 5)
                y_coord = np.random.randint(5, IMG_SIZE - 5)
                radius = np.random.randint(2, 5)
                cv2.circle(img, (x, y_coord), radius, (30, 30, 180), -1)
            img_tensor = img.transpose(2, 0, 1) / 255.0
            X.append(img_tensor)
            y.append(label)
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64)

class AcneCNN(nn.Module):
    def __init__(self):
        super(AcneCNN, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.ReLU(), nn.BatchNorm2d(32), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.BatchNorm2d(64), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.ReLU(), nn.BatchNorm2d(128), nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 8 * 8, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, 3)
        )
    def forward(self, x):
        return self.classifier(self.features(x))

print("Generating training data...")
X, y = generate_synthetic_data(400)
print("Data generated:", X.shape, y.shape)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

train_ds = TensorDataset(torch.tensor(X_train), torch.tensor(y_train))
test_ds  = TensorDataset(torch.tensor(X_test),  torch.tensor(y_test))
train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE)

device = torch.device("cpu")
print("Using device:", device)

model = AcneCNN().to(device)
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

print("Training model...")
for epoch in range(EPOCHS):
    model.train()
    total_loss = 0
    for X_batch, y_batch in train_loader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)
        optimizer.zero_grad()
        output = model(X_batch)
        loss = criterion(output, y_batch)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    print(f"Epoch {epoch+1}/{EPOCHS} — Loss: {total_loss/len(train_loader):.4f}")

model.eval()
correct = 0
total = 0
with torch.no_grad():
    for X_batch, y_batch in test_loader:
        outputs = model(X_batch)
        _, predicted = torch.max(outputs, 1)
        correct += (predicted == y_batch).sum().item()
        total += y_batch.size(0)

print(f"Test Accuracy: {100 * correct / total:.2f}%")
torch.save(model.state_dict(), "acne_model.pth")
print("Model saved as acne_model.pth")