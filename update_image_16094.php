<?php
// WordPress Image Metadata Update Script
// Save this file as update_image_meta.php in your WordPress root directory
// Then run it by visiting: https://xsellpoint.com/update_image_meta.php

// Load WordPress
require_once('wp-load.php');

// Security check - uncomment for production use
// if (!current_user_can('administrator')) {
//     die('Administrator access required');
// }

// Image data
$image_id = 16094;
$product_id = 16125;
$alt_text = 'Your alt text';
$title = '';
$caption = 'Your caption';
$description = 'Your description';

echo "<pre>";
echo "Starting image metadata update...\n";

// 1. Update alt text (stored in postmeta)
if (!empty($alt_text)) {
    $old_alt = get_post_meta($image_id, '_wp_attachment_image_alt', true);
    $result = update_post_meta($image_id, '_wp_attachment_image_alt', $alt_text);
    echo "Alt text update: " . ($result ? "SUCCESS" : "FAILED") . "\n";
    echo "  Old: " . $old_alt . "\n";
    echo "  New: " . $alt_text . "\n\n";
}

// 2. Update title, caption, description (stored in posts table)
$attachment_data = array(
    'ID' => $image_id
);

if (!empty($title)) $attachment_data['post_title'] = $title;
if (!empty($caption)) $attachment_data['post_excerpt'] = $caption;
if (!empty($description)) $attachment_data['post_content'] = $description;

if (count($attachment_data) > 1) {  // Only if we have something besides ID
    $old_attachment = get_post($image_id);
    
    echo "Old values:\n";
    echo "  Title: " . $old_attachment->post_title . "\n";
    echo "  Caption: " . $old_attachment->post_excerpt . "\n";
    echo "  Description: " . $old_attachment->post_content . "\n\n";
    
    $update_result = wp_update_post($attachment_data);
    
    echo "Attachment update: " . ($update_result ? "SUCCESS" : "FAILED") . "\n";
    
    $updated_attachment = get_post($image_id);
    echo "New values:\n";
    echo "  Title: " . $updated_attachment->post_title . "\n";
    echo "  Caption: " . $updated_attachment->post_excerpt . "\n";
    echo "  Description: " . $updated_attachment->post_content . "\n\n";
}

// 3. Update the product's image data in WooCommerce
if ($product_id > 0) {
    echo "Updating WooCommerce product image data...\n";
    
    $product = wc_get_product($product_id);
    if ($product) {
        $gallery_image_ids = $product->get_gallery_image_ids();
        $all_image_ids = array_merge(array($product->get_image_id()), $gallery_image_ids);
        
        if (in_array($image_id, $all_image_ids)) {
            echo "Image found in product images.\n";
            
            // Clear image cache
            clean_post_cache($image_id);
            clean_post_cache($product_id);
            
            // Force WooCommerce to update its cache
            $product = wc_get_product($product_id, array('force_update' => true));
            wc_delete_product_transients($product_id);
            
            echo "Cleared product cache for ID: $product_id\n";
            echo "SUCCESS: WooCommerce product image data updated.\n";
        } else {
            echo "WARNING: Image ID $image_id not found in product $product_id images.\n";
        }
    } else {
        echo "ERROR: Product ID $product_id not found.\n";
    }
}

echo "\nAll updates complete!\n";
echo "</pre>";
?>