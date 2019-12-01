import argparse
from datetime import datetime

import torch
import torch.nn as nn
from torchvision import transforms

from data_loader import get_loader, read_dataset
from model import ClassificationCNN


def train(args):
    # Image preprocessing, normalization for the pretrained resnet
    transform = transforms.Compose([
        transforms.Resize((299, 299)),
        transforms.ToTensor(),
        transforms.Normalize((0.485, 0.456, 0.406),
                             (0.229, 0.224, 0.225))
    ])

    train_dataset, val_dataset = read_dataset(
        args.original_image_dir, args.tampered_image_dir, transform, split=0.8
    )

    # Build data loader
    train_loader = get_loader(
        train_dataset, args.batch_size, shuffle=True, num_workers=args.num_workers
    )
    val_loader = get_loader(
        val_dataset, args.batch_size, shuffle=True, num_workers=args.num_workers
    )

    # Device configuration
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print('training on', device)

    # Build the models
    model = ClassificationCNN().to(device)

    # Loss and optimizer
    criterion = nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)

    now = datetime.now()
    # Train the models
    total_step = len(train_loader)
    for epoch in range(args.num_epochs):
        model.train()
        for i, (images, targets) in enumerate(train_loader):
            # Set mini-batch dataset
            images = images.to(device)
            targets = targets.to(device)

            # Forward, backward and optimize
            outputs = model(images)
            loss = criterion(outputs, targets)
            model.zero_grad()
            loss.backward()
            optimizer.step()

            # Print log info
            if i % args.log_step == 0:
                log_info = 'Epoch [{}/{}], Step [{}/{}], Loss: {:.4f}, Iteration time: {}'.format(
                    epoch, args.num_epochs, i, total_step, loss.item(), datetime.now() - now
                )
                print(log_info)
            now = datetime.now()

        # validation
        model.eval()
        with torch.no_grad():
            loss_values = []
            correct_predictions = 0
            total_predictions = 0

            for images, targets in val_loader:
                images = images.to(device)
                targets = targets.to(device)

                outputs = model(images)
                loss = criterion(outputs, targets)
                loss_values.append(loss)

                predictions = outputs.round()
                cur_correct = int(targets.eq(predictions).sum().cpu())
                correct_predictions += cur_correct
                total_predictions += len(images)

            val_loss = sum(loss_values) / len(loss_values)
            val_accuracy = correct_predictions / total_predictions
            print('Validation - Loss / Acc: {:.3f}/{:.3f}'.format(epoch, args.num_epochs, val_loss, val_accuracy))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_path', type=str, default='models/', help='path for saving trained models')
    parser.add_argument(
        '--original_image_dir', type=str, default='../dataset/images_tiny/original', help='directory for original images'
    )
    parser.add_argument(
        '--tampered_image_dir', type=str, default='../dataset/images_tiny/tampered', help='directory for tamprerd images'
    )
    parser.add_argument('--log_step', type=int, default=10, help='step size for printing log info')
    parser.add_argument('--save_step', type=int, default=1000, help='step size for saving trained models')

    parser.add_argument('--num_epochs', type=int, default=5)
    parser.add_argument('--batch_size', type=int, default=16)
    parser.add_argument('--num_workers', type=int, default=2)
    parser.add_argument('--learning_rate', type=float, default=0.001)
    args = parser.parse_args()
    train(args)


if __name__ == '__main__':
    main()
