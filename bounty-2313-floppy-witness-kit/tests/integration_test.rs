use std::fs;
use std::process::Command;
use tempfile::TempDir;

#[test]
fn test_write_and_read_witness() {
    let temp = TempDir::new().unwrap();
    let witness_file = temp.path().join("test_witness.bin");
    
    // Write a witness
    let output = Command::new("cargo")
        .args(&["run", "--", "write", "--epoch", "100", "--device", witness_file.to_str().unwrap()])
        .current_dir(".")
        .output()
        .expect("Failed to execute write command");
    
    assert!(output.status.success(), "Write command failed: {}", String::from_utf8_lossy(&output.stderr));
    assert!(witness_file.exists(), "Witness file was not created");
    
    // Read the witness
    let output = Command::new("cargo")
        .args(&["run", "--", "read", "--device", witness_file.to_str().unwrap()])
        .current_dir(".")
        .output()
        .expect("Failed to execute read command");
    
    assert!(output.status.success(), "Read command failed");
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("Epoch: 100"), "Epoch not found in output");
    assert!(stdout.contains("Miners:"), "Miners not found in output");
}

#[test]
fn test_verify_witness() {
    let temp = TempDir::new().unwrap();
    let witness_file = temp.path().join("test_witness.bin");
    
    // Create witness
    Command::new("cargo")
        .args(&["run", "--", "write", "--epoch", "200", "--device", witness_file.to_str().unwrap()])
        .current_dir(".")
        .output()
        .expect("Failed to create witness");
    
    // Verify it
    let output = Command::new("cargo")
        .args(&["run", "--", "verify", witness_file.to_str().unwrap()])
        .current_dir(".")
        .output()
        .expect("Failed to execute verify command");
    
    assert!(output.status.success(), "Verify command failed");
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("verification PASSED"), "Verification did not pass");
}

#[test]
fn test_create_floppy_image() {
    let temp = TempDir::new().unwrap();
    let witness1 = temp.path().join("w1.bin");
    let witness2 = temp.path().join("w2.bin");
    let image_file = temp.path().join("disk.img");
    
    // Create two witnesses
    Command::new("cargo")
        .args(&["run", "--", "write", "--epoch", "300", "--device", witness1.to_str().unwrap()])
        .current_dir(".")
        .output()
        .unwrap();
    
    Command::new("cargo")
        .args(&["run", "--", "write", "--epoch", "301", "--device", witness2.to_str().unwrap()])
        .current_dir(".")
        .output()
        .unwrap();
    
    // Create image
    let output = Command::new("cargo")
        .args(&["run", "--", "create-image", "--output", image_file.to_str().unwrap(),
               witness1.to_str().unwrap(), witness2.to_str().unwrap()])
        .current_dir(".")
        .output()
        .expect("Failed to create image");
    
    assert!(output.status.success(), "Create image command failed");
    assert!(image_file.exists(), "Image file was not created");
    
    // Check image size (should be 1.44MB)
    let metadata = fs::metadata(&image_file).unwrap();
    assert_eq!(metadata.len(), 1_440_000, "Image size should be 1.44MB");
    
    // List witnesses in image
    let output = Command::new("cargo")
        .args(&["run", "--", "list", "--device", image_file.to_str().unwrap()])
        .current_dir(".")
        .output()
        .expect("Failed to list witnesses");
    
    assert!(output.status.success(), "List command failed");
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(stdout.contains("2 witnesses"), "Should find 2 witnesses");
}

#[test]
fn test_witness_size_under_100kb() {
    let temp = TempDir::new().unwrap();
    let witness_file = temp.path().join("test_witness.bin");
    
    Command::new("cargo")
        .args(&["run", "--", "write", "--epoch", "999", "--device", witness_file.to_str().unwrap()])
        .current_dir(".")
        .output()
        .expect("Failed to create witness");
    
    let metadata = fs::metadata(&witness_file).unwrap();
    assert!(metadata.len() < 100_000, "Witness should be under 100KB");
    println!("✅ Witness size: {} bytes (under 100KB limit)", metadata.len());
}

#[test]
fn test_many_witnesses_on_floppy() {
    // Calculate how many witnesses fit on a 1.44MB floppy
    let temp = TempDir::new().unwrap();
    let witness_file = temp.path().join("test_witness.bin");
    
    Command::new("cargo")
        .args(&["run", "--", "write", "--epoch", "1", "--device", witness_file.to_str().unwrap()])
        .current_dir(".")
        .output()
        .expect("Failed to create witness");
    
    let metadata = fs::metadata(&witness_file).unwrap();
    let witness_size = metadata.len();
    let floppy_capacity = 1_440_000;
    let estimated_count = floppy_capacity / witness_size;
    
    println!("✅ Single witness size: {} bytes", witness_size);
    println!("✅ Estimated witnesses per 1.44MB floppy: ~{}", estimated_count);
    
    assert!(estimated_count > 1000, "Should fit over 1000 witnesses on a floppy");
}
