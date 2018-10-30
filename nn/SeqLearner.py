import torch.nn as nn
import torch
from utils import SeqUtils
from tqdm import tqdm


class SimpleEncoderDecoder(nn.Module):
    def __init__(self, num_types, device='cuda'):
        super(SimpleEncoderDecoder, self).__init__()
        self.device = device
        self.num_types = num_types
        self.encoder = nn.LSTM(input_size=300, hidden_size=300, bidirectional=True, num_layers=2).to(device)
        self.predictor = nn.Sequential(
            nn.Linear(in_features=300, out_features=self.num_types),
        ).to(device)

    def forward(self, input):
        seq_len = input.shape[0]
        batch_shape = input.shape[1]

        encoder_output, _ = self.encoder(input)
        encoder_output = encoder_output.view(seq_len, batch_shape, 2, self.encoder.hidden_size)
        encoder_output = encoder_output[:, :, 0, :] + encoder_output[:, :, 1, :]
        prediction = self.predictor(encoder_output)
        return prediction.view(-1, self.num_types)  # collapse the time dimension

    def train_epoch(self, dataset, batch_size, criterion, optimizer):
        permutation = torch.randperm(len(dataset))
        loss = 0.
        batch_start = 0

        while batch_start < dataset.len:
            batch_end = min([batch_start + batch_size, len(dataset)])
            batch_xy = [dataset[permutation[i]] for i in range(batch_start, batch_end)]
            batch_x = torch.nn.utils.rnn.pad_sequence([xy[0] for xy in batch_xy if xy]).to(self.device)
            batch_y = torch.nn.utils.rnn.pad_sequence([xy[1] for xy in batch_xy if xy]).long().to(self.device)
            loss += self.train_batch(batch_x, batch_y, criterion, optimizer)
            batch_start += batch_size
        return loss

    def eval_epoch(self, dataset, batch_size, criterion):
        loss = 0.
        batch_start = 0
        while batch_start < dataset.len:
            batch_end = min([batch_start + batch_size, len(dataset)])
            batch_xy = [dataset[i] for i in range(batch_start, batch_end)]
            batch_x = torch.nn.utils.rnn.pad_sequence([xy[0] for xy in batch_xy if xy]).to(self.device)
            batch_y = torch.nn.utils.rnn.pad_sequence([xy[1] for xy in batch_xy if xy]).long().to(self.device)
            loss += self.eval_batch(batch_x, batch_y, criterion)
            batch_start += batch_size
        return loss

    def train_batch(self, batch_x, batch_y, criterion, optimizer):
        self.train()
        optimizer.zero_grad()
        prediction = self.forward(batch_x)
        loss = criterion(prediction, batch_y.view(-1))
        loss.backward()
        optimizer.step()
        return loss.item()

    def eval_batch(self, batch_x, batch_y, criterion):
        self.eval()
        prediction = self.forward(batch_x)
        loss = criterion(prediction, batch_y.view(-1))
        return loss.item()

    def accuracy(self, predictions, ground_truth):
        predictions = torch.argmax(predictions, dim=1).float()
        # todo
        raise NotImplementedError


def __main__(fake=False):
    s, dl = SeqUtils.__main__(fake=fake)

    device = ('cuda' if torch.cuda.is_available() else 'cpu')
    ecdc = SimpleEncoderDecoder(len(s.types), device)
    criterion = nn.CrossEntropyLoss(ignore_index=0, reduction='sum')
    optimizer = torch.optim.Adam(ecdc.parameters())

    num_epochs = 100
    batch_size = 64

    for i in range(num_epochs):
        print('------------------ Epoch {} ------------------'.format(i))
        print(' Training Loss: {}'.format(ecdc.train_epoch(s, batch_size, criterion, optimizer)))