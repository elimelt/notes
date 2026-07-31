import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import load_digits
from time import time

def compress_image(image, n_components):
    """
    Compress image using PCA by keeping only the top n_components.
    Returns compressed image and compression ratio.
    """
    mean = np.mean(image, axis=0)
    centered = image - mean
    
    # get covariance matrix and eigenvectors
    cov_matrix = np.cov(centered.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov_matrix)
    
    # sort eigenvectors by eigenvalues in descending order
    idx = np.argsort(eigenvalues)[::-1]
    eigenvectors = eigenvectors[:, idx]
    
    # keep only top n_components
    reduced_vecs = eigenvectors[:, :n_components]
    
    # project data onto reduced eigenvectors
    projected = centered @ reduced_vecs
    
    # reconstruct the image
    reconstructed = projected @ reduced_vecs.T + mean
    
    # compression ratio
    original_size = image.size * 8  # assuming 8 bits per number
    compressed_size = (projected.size + reduced_vecs.size + mean.size) * 8
    compression_ratio = original_size / compressed_size
    
    return reconstructed, compression_ratio, projected, reduced_vecs

def plot_compression_results(original, reconstructed, n_components, compression_ratio):
    plt.figure(figsize=(12, 4))
    
    plt.subplot(121)
    plt.imshow(original, cmap='gray')
    plt.title('Original Image')
    plt.axis('off')
    
    plt.subplot(122)
    plt.imshow(reconstructed, cmap='gray')
    plt.title(f'Reconstructed with {n_components} components\n'
              f'Compression ratio: {compression_ratio:.1f}x')
    plt.axis('off')
    
    plt.tight_layout()
    
def main():
    digits = load_digits()
    
    digit_8_idx = np.where(digits.target == 8)[0][0]
    image = digits.data[digit_8_idx].reshape(8, 8)
    
    n_components_list = [1, 2, 3, 4, 5, 6, 7, 8]
    plt.figure(figsize=(15, 8))
    
    for i, n in enumerate(n_components_list, 1):
        reconstructed, ratio, _, _ = compress_image(image, n)
        
        plt.subplot(2, 4, i)
        plt.imshow(reconstructed, cmap='gray')
        plt.title(f'{n} components\nRatio: {ratio:.1f}x')
        plt.axis('off')
    
    plt.suptitle('Image Reconstruction with Different Numbers of Components', y=1.02)
    plt.tight_layout()
    
    # Now let's analyze compression performance
    n_samples = 100
    test_images = digits.data[:n_samples]
    
    compression_results = []
    timing_results = []
    
    for n in n_components_list:
        total_ratio = 0
        start_time = time()
        
        for img in test_images:
            img_2d = img.reshape(8, 8)
            _, ratio, _, _ = compress_image(img_2d, n)
            total_ratio += ratio
            
        avg_ratio = total_ratio / n_samples
        total_time = time() - start_time
        
        compression_results.append(avg_ratio)
        timing_results.append(total_time)
    
    plt.figure(figsize=(12, 4))
    
    plt.subplot(121)
    plt.plot(n_components_list, compression_results, 'bo-')
    plt.xlabel('Number of Components')
    plt.ylabel('Average Compression Ratio')
    plt.title('Compression Performance')
    plt.grid(True)
    
    plt.subplot(122)
    plt.plot(n_components_list, timing_results, 'ro-')
    plt.xlabel('Number of Components')
    plt.ylabel('Processing Time (seconds)')
    plt.title(f'Processing Time for {n_samples} Images')
    plt.grid(True)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()