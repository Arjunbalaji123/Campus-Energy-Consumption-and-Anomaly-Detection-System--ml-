"""Pure NumPy / Scikit-learn Compatible LSTM Sequence Regressor.

Implements Long Short-Term Memory (LSTM) cell mathematics, Backpropagation
Through Time (BPTT), and Adam optimization for sequence-based energy prediction.
"""
import os
import time
from typing import Tuple, List, Optional, Dict, Any
import numpy as np
import joblib


class CITLSTMRegressor:
    """Long Short-Term Memory (LSTM) Sequence Regressor for Time-Series Energy Forecasting."""

    def __init__(
        self,
        input_dim: int = 8,
        hidden_dim: int = 32,
        sequence_length: int = 24,
        random_state: int = 42
    ):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.sequence_length = sequence_length
        self.random_state = random_state

        np.random.seed(random_state)
        # Xavier/Glorot Initialization for LSTM Gates (Forget, Input, Candidate, Output)
        limit_x = np.sqrt(6.0 / (input_dim + hidden_dim))
        limit_h = np.sqrt(6.0 / (hidden_dim + hidden_dim))

        # W: (input_dim, 4 * hidden_dim), U: (hidden_dim, 4 * hidden_dim), b: (4 * hidden_dim)
        self.W = np.random.uniform(-limit_x, limit_x, (input_dim, 4 * hidden_dim))
        self.U = np.random.uniform(-limit_h, limit_h, (hidden_dim, 4 * hidden_dim))
        self.b = np.zeros(4 * hidden_dim)
        # Initialize forget gate bias to 1.0 (prevents vanishing gradients early in training)
        self.b[:hidden_dim] = 1.0

        # Linear Output Projection Head: (hidden_dim, 1)
        self.Wy = np.random.uniform(-0.1, 0.1, (hidden_dim, 1))
        self.by = np.zeros(1)

        # Adam Optimizer Moments
        self.params = [self.W, self.U, self.b, self.Wy, self.by]
        self.m = [np.zeros_like(p) for p in self.params]
        self.v = [np.zeros_like(p) for p in self.params]
        self.t_step = 0

    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -15.0, 15.0)))

    def forward(self, X_batch: np.ndarray) -> Tuple[np.ndarray, List[Dict[str, np.ndarray]]]:
        """Forward pass through time steps 0 ... L-1.
        
        Args:
            X_batch: (B, L, D) array of input sequences.
            
        Returns:
            y_pred: (B, 1) predictions.
            cache: Timestep activations needed for BPTT.
        """
        B, L, _ = X_batch.shape
        H = self.hidden_dim

        h = np.zeros((B, H))
        c = np.zeros((B, H))
        cache = []

        for t in range(L):
            xt = X_batch[:, t, :]  # (B, D)
            gates = np.dot(xt, self.W) + np.dot(h, self.U) + self.b  # (B, 4H)

            f = self._sigmoid(gates[:, :H])
            i = self._sigmoid(gates[:, H:2*H])
            c_cand = np.tanh(gates[:, 2*H:3*H])
            o = self._sigmoid(gates[:, 3*H:])

            c_next = f * c + i * c_cand
            tanh_c = np.tanh(c_next)
            h_next = o * tanh_c

            cache.append({
                "xt": xt,
                "h_prev": h,
                "c_prev": c,
                "f": f,
                "i": i,
                "c_cand": c_cand,
                "o": o,
                "c": c_next,
                "tanh_c": tanh_c,
                "h": h_next,
            })

            h = h_next
            c = c_next

        # Final prediction from last hidden state h_L
        y_pred = np.dot(h, self.Wy) + self.by
        return y_pred, cache

    def backward(self, X_batch: np.ndarray, y_batch: np.ndarray, y_pred: np.ndarray, cache: List[Dict[str, np.ndarray]]) -> List[np.ndarray]:
        """Backpropagation Through Time (BPTT)."""
        B, L, _ = X_batch.shape
        H = self.hidden_dim

        # Loss: Mean Squared Error (MSE)
        dy = (y_pred - y_batch) * (2.0 / B)  # (B, 1)

        dWy = np.dot(cache[-1]["h"].T, dy)  # (H, 1)
        dby = np.sum(dy, axis=0)           # (1,)

        dh = np.dot(dy, self.Wy.T)         # (B, H)
        dc = np.zeros((B, H))

        dW = np.zeros_like(self.W)
        dU = np.zeros_like(self.U)
        db = np.zeros_like(self.b)

        # Backpropagate backwards through time
        for t in reversed(range(L)):
            step = cache[t]
            xt = step["xt"]
            h_prev = step["h_prev"]
            c_prev = step["c_prev"]
            f = step["f"]
            i = step["i"]
            c_cand = step["c_cand"]
            o = step["o"]
            c = step["c"]
            tanh_c = step["tanh_c"]

            # Gradient into hidden state
            do = dh * tanh_c
            dc += dh * o * (1.0 - tanh_c ** 2)

            df = dc * c_prev
            di = dc * c_cand
            dc_cand = dc * i

            # Gate pre-activations derivatives
            dz_f = df * f * (1.0 - f)
            dz_i = di * i * (1.0 - i)
            dz_c = dc_cand * (1.0 - c_cand ** 2)
            dz_o = do * o * (1.0 - o)

            dz = np.hstack([dz_f, dz_i, dz_c, dz_o])  # (B, 4H)

            dW += np.dot(xt.T, dz)
            dU += np.dot(h_prev.T, dz)
            db += np.sum(dz, axis=0)

            # Pass gradients to previous timestep
            dh = np.dot(dz, self.U.T)
            dc = dc * f

        grads = [dW, dU, db, dWy, dby]
        # Gradient clipping to prevent gradient explosion
        for g in grads:
            np.clip(g, -5.0, 5.0, out=g)

        return grads

    def _adam_step(self, grads: List[np.ndarray], lr: float, beta1: float = 0.9, beta2: float = 0.999, eps: float = 1e-8):
        """Adam optimizer parameter update."""
        self.t_step += 1
        for idx in range(len(self.params)):
            g = grads[idx]
            self.m[idx] = beta1 * self.m[idx] + (1.0 - beta1) * g
            self.v[idx] = beta2 * self.v[idx] + (1.0 - beta2) * (g ** 2)

            m_hat = self.m[idx] / (1.0 - beta1 ** self.t_step)
            v_hat = self.v[idx] / (1.0 - beta2 ** self.t_step)

            self.params[idx] -= lr * m_hat / (np.sqrt(v_hat) + eps)

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        epochs: int = 25,
        batch_size: int = 64,
        lr: float = 0.005,
        verbose: bool = True
    ) -> List[float]:
        """Train LSTM network using mini-batch gradient descent and Adam."""
        N = X_train.shape[0]
        history = []

        for ep in range(1, epochs + 1):
            indices = np.random.permutation(N)
            epoch_loss = 0.0
            n_batches = 0

            for i in range(0, N, batch_size):
                b_idx = indices[i:i + batch_size]
                xb = X_train[b_idx]
                yb = y_train[b_idx]

                pred, cache = self.forward(xb)
                loss = float(np.mean((pred - yb) ** 2))
                epoch_loss += loss
                n_batches += 1

                grads = self.backward(xb, yb, pred, cache)
                self._adam_step(grads, lr=lr)

            avg_loss = epoch_loss / max(n_batches, 1)
            history.append(avg_loss)

            if verbose and (ep == 1 or ep % 5 == 0 or ep == epochs):
                print(f"Epoch {ep:2d}/{epochs:2d} - MSE Loss: {avg_loss:.5f}")

        return history

    def predict(self, X_seq: np.ndarray, batch_size: int = 128) -> np.ndarray:
        """Generate predictions for sequential samples."""
        N = X_seq.shape[0]
        preds = []
        for i in range(0, N, batch_size):
            xb = X_seq[i:i + batch_size]
            yp, _ = self.forward(xb)
            preds.append(yp)
        return np.vstack(preds) if preds else np.zeros((0, 1))

    def save(self, filepath: str):
        """Serialize model weights and metadata to disk."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        payload = {
            "W": self.W,
            "U": self.U,
            "b": self.b,
            "Wy": self.Wy,
            "by": self.by,
            "input_dim": self.input_dim,
            "hidden_dim": self.hidden_dim,
            "sequence_length": self.sequence_length,
            "random_state": self.random_state,
        }
        joblib.dump(payload, filepath)

    @classmethod
    def load(cls, filepath: str) -> "CITLSTMRegressor":
        """Deserialize trained model from disk."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file not found at: {filepath}")
        data = joblib.load(filepath)
        model = cls(
            input_dim=data["input_dim"],
            hidden_dim=data["hidden_dim"],
            sequence_length=data["sequence_length"],
            random_state=data["random_state"]
        )
        model.W = data["W"]
        model.U = data["U"]
        model.b = data["b"]
        model.Wy = data["Wy"]
        model.by = data["by"]
        model.params = [model.W, model.U, model.b, model.Wy, model.by]
        return model

