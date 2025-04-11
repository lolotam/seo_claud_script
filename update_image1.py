#!/usr/bin/env python
"""
WordPress Image Metadata Direct Updater

This standalone script updates image metadata (caption, description, alt text)
for a specific product image in WordPress.

Requirements:
pip install requests
"""

import requests
import json
import os
import sys
import time
import argparse

# Command-line arguments
parser = argparse.ArgumentParser(description='WordPress Image Metadata Direct Updater')
parser.add_argument('--image-id', type=int, required=True, help='WordPress attachment/image ID')
parser.add_argument('--product-id', type=int, required=True, help='WooCommerce product ID')
parser.add_argument('--alt-text', type=str, help='Alt text for the image')
parser.add_argument('--title', type=str, help='Title for the image')
parser.add_argument('--caption', type=str, help='Caption for the image')
parser.add_argument('--description', type=str, help='Description for the image')
parser.add_argument('--json-file', type=str, help='JSON file containing metadata (alternative to individual args)')
args = parser.parse_args()

# WordPress credentials
WP_USERNAME = "lolotam"
WP_PASSWORD = "@Ww55683677wW@"

# WooCommerce credentials
WC_CONSUMER_KEY = "ck_ad9577c47151c4fa50ca6ee85dd2a58d2d6e6e79"
WC_CONSUMER_SECRET = "cs_dc38dd138ae05842942ed84ff64a207a4b41b109"

# URLs
WP_SITE_URL = "https://xsellpoint.com"
WP_REST_API_URL = f"{WP_SITE_URL}/wp-json/wp/v2"
WP_ADMIN_AJAX_URL = f"{WP_SITE_URL}/wp-admin/admin-ajax.php"
WP_LOGIN_URL = f"{WP_SITE_URL}/wp-login.php"
WC_API_URL = f"{WP_SITE_URL}/wp-json/wc/v3"

# Load metadata from JSON file if provided
if args.json_file and os.path.exists(args.json_file):
    try:
        with open(args.json_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            
        # Extract values from the JSON
        alt_text = metadata.get('alt_text', args.alt_text)
        title = metadata.get('image_title', args.title)
        caption = metadata.get('image_caption', args.caption)
        description = metadata.get('image_description', args.description)
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        sys.exit(1)
else:
    # Use command-line arguments
    alt_text = args.alt_text
    title = args.title
    caption = args.caption
    description = args.description

# Validate we have the image_id and at least one metadata field
if not args.image_id:
    print("Error: Image ID is required")
    sys.exit(1)

if not any([alt_text, title, caption, description]):
    print("Error: At least one metadata field (alt_text, title, caption, description) is required")
    sys.exit(1)

print(f"Updating image ID {args.image_id} with:")
if alt_text: print(f"- Alt text: {alt_text}")
if title: print(f"- Title: {title}")
if caption: print(f"- Caption: {caption}")
if description: print(f"- Description: {description}")
print()

def update_via_wc_product_api():
    """Update image metadata via WooCommerce Product API"""
    print("\nMethod 1: Using WooCommerce Product API...")
    
    # First get the current product data
    try:
        get_response = requests.get(
            f"{WC_API_URL}/products/{args.product_id}",
            auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET),
            timeout=30
        )
        
        if get_response.status_code != 200:
            print(f"❌ Failed to get product: Status {get_response.status_code}")
            return False
        
        product_data = get_response.json()
        
        # Check if the product has images
        if not product_data.get('images'):
            print("❌ Product has no images")
            return False
        
        # Find our image in the product images
        image_found = False
        updated_images = []
        
        for image in product_data['images']:
            if image.get('id') == args.image_id:
                image_found = True
                # Update this image's metadata
                updated_image = image.copy()
                if alt_text: updated_image['alt'] = alt_text
                if title: updated_image['name'] = title
                if caption: updated_image['caption'] = caption
                if description: updated_image['description'] = description
                updated_images.append(updated_image)
            else:
                updated_images.append(image)
        
        if not image_found:
            print(f"❌ Image ID {args.image_id} not found in product images")
            return False
        
        # Update the product with modified images
        update_data = {
            'images': updated_images
        }
        
        update_response = requests.put(
            f"{WC_API_URL}/products/{args.product_id}",
            auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET),
            json=update_data,
            timeout=30
        )
        
        if update_response.status_code in [200, 201]:
            print(f"✅ Successfully updated image metadata via WooCommerce Product API")
            return True
        else:
            print(f"❌ Failed to update product: Status {update_response.status_code}")
            print(f"Response: {update_response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def update_via_wp_rest_api():
    """Update image metadata via WordPress REST API"""
    print("\nMethod 2: Using WordPress REST API...")
    
    # Prepare the data payload
    data = {}
    if title: data['title'] = title
    if caption: data['caption'] = caption
    if description: data['description'] = description
    if alt_text: data['alt_text'] = alt_text
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Create a session for cookie handling
    session = requests.Session()
    
    try:
        # First authenticate with WordPress
        login_data = {
            'log': WP_USERNAME,
            'pwd': WP_PASSWORD,
            'rememberme': 'forever',
            'redirect_to': f"{WP_SITE_URL}/wp-admin/",
            'testcookie': '1'
        }
        
        # Login and get cookies
        login_response = session.post(
            WP_LOGIN_URL,
            data=login_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30
        )
        
        if "wordpress_logged_in" not in str(session.cookies):
            print("❌ WordPress login failed - no login cookie received")
            # Try to parse error message from response
            if "ERROR" in login_response.text:
                import re
                error_pattern = r'<div id="login_error">\s*<strong>Error</strong>:([^<]+)'
                error_match = re.search(error_pattern, login_response.text)
                if error_match:
                    print(f"  Login error: {error_match.group(1).strip()}")
            return False
            
        print("✅ Successfully logged in to WordPress")
        
        # Get the nonce first (required for API operations)
        nonce_response = session.get(f"{WP_SITE_URL}/wp-admin/admin-ajax.php?action=rest-nonce", timeout=30)
        rest_nonce = nonce_response.text.strip()
        
        if not rest_nonce or len(rest_nonce) < 5:
            print("❌ Failed to get WordPress REST nonce")
            print(f"Response: {nonce_response.text[:100]}")
            return False
            
        print(f"✅ Got WordPress REST nonce: {rest_nonce[:5]}...")
        
        # Add nonce to headers
        headers['X-WP-Nonce'] = rest_nonce
        
        # Now update the attachment
        update_response = session.post(
            f"{WP_REST_API_URL}/media/{args.image_id}",
            json=data,
            headers=headers,
            timeout=30
        )
        
        print(f"Response status: {update_response.status_code}")
        print(f"Response headers: {dict(update_response.headers)}")
        print(f"Response body: {update_response.text[:200]}...")
        
        if update_response.status_code in [200, 201]:
            print(f"✅ Successfully updated image metadata via WordPress REST API")
            
            # Also update alt text via postmeta if provided
            if alt_text:
                alt_update_success = update_alt_text_via_ajax(session, rest_nonce)
                print(f"Alt text update via AJAX: {'✅ Success' if alt_update_success else '❌ Failed'}")
            
            return True
        else:
            print(f"❌ Failed to update via REST API: Status {update_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

def update_alt_text_via_ajax(session, nonce):
    """Update image alt text via admin-ajax.php (separate method because it's stored differently)"""
    try:
        print("\nUpdating alt text via admin-ajax.php...")
        
        ajax_data = {
            'action': 'update_attachment_alt_text',
            'attachment_id': args.image_id,
            'alt_text': alt_text,
            '_wpnonce': nonce
        }
        
        # We need to create a custom action for this
        # This is the PHP code needed in your theme's functions.php:
        """
        add_action('wp_ajax_update_attachment_alt_text', 'update_attachment_alt_text');
        function update_attachment_alt_text() {
            $attachment_id = intval($_POST['attachment_id']);
            $alt_text = sanitize_text_field($_POST['alt_text']);
            
            // Check permissions
            if (!current_user_can('edit_post', $attachment_id)) {
                wp_send_json_error('Permission denied');
                return;
            }
            
            // Update alt text meta
            update_post_meta($attachment_id, '_wp_attachment_image_alt', $alt_text);
            wp_send_json_success('Alt text updated');
        }
        """
        
        # Create a generic update post meta function if the custom action doesn't exist
        ajax_data_generic = {
            'action': 'update_post_meta',
            'post_id': args.image_id,
            'meta_key': '_wp_attachment_image_alt',
            'meta_value': alt_text,
            '_wpnonce': nonce
        }
        
        # Try with custom action first
        ajax_response = session.post(
            WP_ADMIN_AJAX_URL,
            data=ajax_data,
            timeout=30
        )
        
        # If that fails, try the generic approach
        if "success" not in ajax_response.text.lower():
            ajax_response = session.post(
                WP_ADMIN_AJAX_URL,
                data=ajax_data_generic,
                timeout=30
            )
        
        return "success" in ajax_response.text.lower()
        
    except Exception as e:
        print(f"❌ Error updating alt text: {str(e)}")
        return False

def generate_php_script():
    """Generate a PHP script for manual update"""
    print("\nGenerating PHP script for manual update...")
    
    # Create the PHP script
    php_code = f"""<?php
// WordPress Image Metadata Update Script
// Save this file as update_image_meta.php in your WordPress root directory
// Then run it by visiting: https://xsellpoint.com/update_image_meta.php

// Load WordPress
require_once('wp-load.php');

// Security check - uncomment for production use
// if (!current_user_can('administrator')) {{
//     die('Administrator access required');
// }}

// Image data
$image_id = {args.image_id};
$product_id = {args.product_id};
$alt_text = '{alt_text if alt_text else ""}';
$title = '{title if title else ""}';
$caption = '{caption if caption else ""}';
$description = '{description if description else ""}';

echo "<pre>";
echo "Starting image metadata update...\\n";

// 1. Update alt text (stored in postmeta)
if (!empty($alt_text)) {{
    $old_alt = get_post_meta($image_id, '_wp_attachment_image_alt', true);
    $result = update_post_meta($image_id, '_wp_attachment_image_alt', $alt_text);
    echo "Alt text update: " . ($result ? "SUCCESS" : "FAILED") . "\\n";
    echo "  Old: " . $old_alt . "\\n";
    echo "  New: " . $alt_text . "\\n\\n";
}}

// 2. Update title, caption, description (stored in posts table)
$attachment_data = array(
    'ID' => $image_id
);

if (!empty($title)) $attachment_data['post_title'] = $title;
if (!empty($caption)) $attachment_data['post_excerpt'] = $caption;
if (!empty($description)) $attachment_data['post_content'] = $description;

if (count($attachment_data) > 1) {{  // Only if we have something besides ID
    $old_attachment = get_post($image_id);
    
    echo "Old values:\\n";
    echo "  Title: " . $old_attachment->post_title . "\\n";
    echo "  Caption: " . $old_attachment->post_excerpt . "\\n";
    echo "  Description: " . $old_attachment->post_content . "\\n\\n";
    
    $update_result = wp_update_post($attachment_data);
    
    echo "Attachment update: " . ($update_result ? "SUCCESS" : "FAILED") . "\\n";
    
    $updated_attachment = get_post($image_id);
    echo "New values:\\n";
    echo "  Title: " . $updated_attachment->post_title . "\\n";
    echo "  Caption: " . $updated_attachment->post_excerpt . "\\n";
    echo "  Description: " . $updated_attachment->post_content . "\\n\\n";
}}

// 3. Update the product's image data in WooCommerce
if ($product_id > 0) {{
    echo "Updating WooCommerce product image data...\\n";
    
    $product = wc_get_product($product_id);
    if ($product) {{
        $gallery_image_ids = $product->get_gallery_image_ids();
        $all_image_ids = array_merge(array($product->get_image_id()), $gallery_image_ids);
        
        if (in_array($image_id, $all_image_ids)) {{
            echo "Image found in product images.\\n";
            
            // Clear image cache
            clean_post_cache($image_id);
            clean_post_cache($product_id);
            
            // Force WooCommerce to update its cache
            $product = wc_get_product($product_id, array('force_update' => true));
            wc_delete_product_transients($product_id);
            
            echo "Cleared product cache for ID: $product_id\\n";
            echo "SUCCESS: WooCommerce product image data updated.\\n";
        }} else {{
            echo "WARNING: Image ID $image_id not found in product $product_id images.\\n";
        }}
    }} else {{
        echo "ERROR: Product ID $product_id not found.\\n";
    }}
}}

echo "\\nAll updates complete!\\n";
echo "</pre>";
?>"""
    
    # Save the PHP script
    script_filename = f"update_image_{args.image_id}.php"
    with open(script_filename, 'w', encoding='utf-8') as f:
        f.write(php_code)
    
    print(f"✅ Generated PHP script: {script_filename}")
    print(f"To use this script:")
    print(f"1. Upload {script_filename} to your WordPress root directory")
    print(f"2. Visit https://xsellpoint.com/{script_filename} in your browser")
    print(f"3. Delete the script after use for security")
    
    return True

# Execute all methods
print("Executing direct update methods...\n")

# Method 1: WooCommerce API
wc_success = update_via_wc_product_api()

# Method 2: WordPress REST API
wp_success = update_via_wp_rest_api()

# Method 3: Generate PHP script for manual update (always do this)
php_script = generate_php_script()

print("\nSummary:")
print(f"- WooCommerce API method: {'✅ Success' if wc_success else '❌ Failed'}")
print(f"- WordPress REST API method: {'✅ Success' if wp_success else '❌ Failed'}")
print(f"- PHP script generated: {'✅ Success' if php_script else '❌ Failed'}")

if wc_success or wp_success:
    print("\n✅ Image metadata updated successfully by at least one method!")
    sys.exit(0)
else:
    print("\n⚠️ Automatic updates failed. Please use the generated PHP script.")
    sys.exit(1)